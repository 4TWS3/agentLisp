"""AgentLisp 全局 pytest conftest：
1. pytest-bdd 的 Gherkin 中文关键字（zh-CN）兼容（pytest-bdd 7 内置；此 conftest 提供兜底别名）。
2. 把 BDD scenarios 的 tag (@FR-CHECK-1 / @FR-RUN-3 / @NFR-* …… 等以 @SRS-ID 形式标注)
   自动映射为已经注册的 @pytest.mark.req("FR-CHECK-1")，保证严格模式
   `-W error::pytest.PytestUnknownMarkWarning` 下不因为未知 tag 挂掉，且
   与 SRS 29148 Traceability Matrix 已有 marker 统一（junit XML 一份即可导出）。
3. pytest_bdd 的自由 tag（@KV-Alignment 这样的「非 SRS-ID 标签」）在严格模式下会被当
   作 Unknown pytest marker 报错。此 conftest 注册 pytest_bdd_apply_tag hook，
   对所有非 SRS-ID / 非 pytest 内置 marker，统一转成 @pytest.mark.tag(name=KV-Alignment)
  （marker 在 pyproject.toml 注册 tag，严格模式就不会报错）。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

import pytest


# --------- 0. 注册 pytest-bdd 的 tag filter hook，所有自由标签先映射到 pytest.mark.tag --------
def pytest_configure(config: Any) -> None:
    """确保 pyproject.toml 里的 markers 生效；这里额外做一次 addin 兜底，
    避免 pyproject.toml markers 顺序没加载到的情况。"""
    for line in _EXTRA_MARKERS:
        config.addinivalue_line("markers", line)


_EXTRA_MARKERS: list[str] = [
    "tag(name): BDD/Gherkin 自定义标签（非 SRS-ID 的自由标签全部映射到 tag(name=...) 避免 PytestUnknownMarkWarning）",
]


@pytest.fixture
def tc(test_context):
    """BDD step 常用的测试上下文别名（简写 tc = test_context）。
    有些 step lambda 里用参数名 tc 代替 test_context，这里提供 fixture 别名避免 FixtureLookupError。
    """
    return test_context


@pytest.fixture(autouse=True)
def _record_req_markers_to_junitxml(record_property: Any, request: Any) -> None:
    """把每个测试用例上的 `req("FR-CHECK-1")` marker 记录成 junitxml testcase
    property，便于 traceability_matrix 脚本导出 SRS-ID → scenario 矩阵。"""
    try:
        for marker in request.node.iter_markers(name="req"):
            if marker.args and isinstance(marker.args[0], str):
                record_property("req", marker.args[0])
        for marker in request.node.iter_markers(name="tag"):
            name = (
                marker.kwargs.get("name")
                if marker.kwargs
                else (marker.args[0] if marker.args else None)
            )
            if isinstance(name, str):
                record_property("tag", name)
    except Exception:
        pass


# --------- 1. Tag → req marker 自动映射（pytest_collection_modifyitems hook）--------
# 合法 SRS-ID 正则：FR-<NAME>-<NUM> / NFR-<CATEGORY>-<NUMa?> / AC-<NUM> / IF-<NAME>-<NUM> / R-<NUM>
_SRS_ID_RE = re.compile(
    r"^(?:"
    r"FR-[A-Z]+-\d+[a-z]?|"
    r"NFR-[A-Z]+-\d+[a-z]?|"
    r"AC-\d+|"
    r"IF-[A-Z]+-\d+|"
    r"R-\d+"
    r")$"
)

# pytest 内置 marker（不能当作 req / tag 映射）
_BUILTIN_MARKERS = frozenset(
    {
        "parametrize",
        "xfail",
        "xpass",
        "skip",
        "skipif",
        "usefixtures",
        "filterwarnings",
        "asyncio",
        "req",
        "bdd",
        "tag",
        "pytest_bdd",
        "scenario",
        "features",
        "allure",
        "allure_label",
        "allure_id",  # allure 也常用，先排除
    }
)


def pytest_bdd_apply_tag(tag: str, function: Any) -> bool:
    """pytest-bdd 9.x hook：返回 True 表示「我已经消费了这个 tag，别再 getattr(pytest.mark, tag)」。

    策略：
      - tag 是合法 SRS-ID → 叠加 req(tag) marker；返回 True（已经处理）
      - 否则 → 叠加 tag(name=tag) marker（已经在 pyproject + 此处 addinivalue_line 注册）
    """
    if tag in _BUILTIN_MARKERS:
        return False
    if _SRS_ID_RE.match(tag):
        marker = pytest.mark.req(tag)
        marker(function)
        return True
    # 自由标签（KV-Alignment / Unguarded-Tool 等）→ 映射到 tag(name=...)
    marker = pytest.mark.tag(name=tag)
    marker(function)
    return True


def pytest_collection_modifyitems(config: Any, items: Iterable[pytest.Item]) -> None:
    """兜底：对所有收集到的 item，扫描 own_markers 中名字匹配 SRS-ID 但没打上 req 的再补一次。
    对非 SRS-ID / 非内置的 marker，若用户（或插件）绕过 pytest_bdd_apply_tag 直接加上的，
    也统一替换成 tag(name=...)，保证严格模式无 PytestUnknownMarkWarning。
    """
    del config  # unused
    for item in list(items):
        # (a) 扫描需要转为 tag(name=...) 的 unknown markers
        known_req_ids: set[str] = set()
        for marker in item.iter_markers(name="req"):
            if marker.args and isinstance(marker.args[0], str):
                known_req_ids.add(marker.args[0])

        # (b) SRS-ID 自动叠加 req（兜底）
        new_own_markers: list[Any] = []
        for marker in list(getattr(item, "own_markers", []) or []):
            name = getattr(marker, "name", None)
            if not name:
                new_own_markers.append(marker)
                continue
            if name in _BUILTIN_MARKERS or name == "tag":
                new_own_markers.append(marker)
                continue
            if _SRS_ID_RE.match(name):
                # SRS-ID 类的标记 → 保留原 marker 同时叠加 req（pytest-bdd 仍要原 marker 做 -m 过滤）
                new_own_markers.append(marker)
                if name not in known_req_ids:
                    item.add_marker(pytest.mark.req(name))
                    known_req_ids.add(name)
                continue
            # 其它自由标签 → 替换为 pytest.mark.tag(name=...)，避免 unknown mark
            new_own_markers.append(pytest.mark.tag(name=name))
        # 原地替换 own_markers
        try:
            object.__setattr__(item, "own_markers", new_own_markers)
        except Exception:
            # 某些 pytest 版本 item.own_markers 是 frozen 的，放过（上面 pytest_bdd_apply_tag 已经处理绝大部分）
            pass
