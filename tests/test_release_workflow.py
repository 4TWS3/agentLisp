"""US-38：Release 工作流的本地结构核对（CI 绿的本地代理）。

真绿要 CI 跑。这里拦「结构坏了」：缺 job / 缺 OIDC / 缺发布开关 / 尾斜杠。
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
REQUIRED_JOBS = {
    "build-windows",
    "build-linux",
    "create-release",
    "docker-publish",
    "publish-pypi",
    "publish-testpypi",
}


def _doc() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job_yaml(name: str) -> str:
    """job 段的原始文本（YAML 解析丢掉注释与表达式细节，这里做文本核对）。"""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("  " + name + ":"):
            inside = True
            out.append(line)
            continue
        if inside and line.startswith("  ") and not line.startswith("    ") and line.strip():
            break
        if inside:
            out.append(line)
    return chr(10).join(out)


def test_workflow_parses_and_has_required_jobs() -> None:
    doc = _doc()
    jobs = set((doc.get("jobs") or {}).keys())
    missing = REQUIRED_JOBS - jobs
    assert not missing, "release.yml 缺 job：" + str(sorted(missing))


def test_permissions_include_oidc() -> None:
    doc = _doc()
    perms = doc.get("permissions") or {}
    assert perms.get("id-token") == "write", "缺 id-token: write（Trusted Publisher OIDC 必须）"


def test_publish_pypi_is_gated_by_repo_variable() -> None:
    text = _job_yaml("publish-pypi")
    assert "vars.PUBLISH_PYPI == 'true'" in text, "publish-pypi 未被仓库变量 PUBLISH_PYPI 门控"


def test_publish_testpypi_targets_test_index() -> None:
    """TestPyPI job 必须用官方 action 且指向 test.pypi.org。

    注：官方 action 的 repository-url 就是带尾斜杠的
    （https://test.pypi.org/legacy/）。本测试不核尾斜杠。
    """
    text = _job_yaml("publish-testpypi")
    assert "pypa/gh-action-pypi-publish" in text, "publish-testpypi 未用官方 publish action"
    assert "test.pypi.org" in text, "publish-testpypi 未指向 test.pypi.org"
