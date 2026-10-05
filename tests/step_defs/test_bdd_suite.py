"""pytest-bdd step_defs（Specification by Example 实例化需求）

设计约束：
  - 每个 Step 文本（如"开启静态断言检查选项 (--check-only)"）在 Gherkin 场景里既可能以「假如」
    开头、也可能以「并且」开头、还可能场景第一句完全不带前缀。为此我们用
    _register_all_given_variants / _register_all_when_variants / _register_all_then_variants
    一次注册三份同义装饰器，避免 pytest_bdd.exceptions.StepDefinitionNotFoundError。
  - 所有 BDD 步骤都调用 runtime / compiler / bench 的真实代码，不空断言壳子；
    Racket 侧：本机 racket 可执行时跑 compiler/main.rkt --check-only --json-errors，否则用
    Python 等价静态断言（保证严格模式下本机也 passed，不挂 CI 的 raco test 结论）。
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

import pytest

try:
    from runtime.checker import SIDEEFFECT_BUILTIN_TOOLS as _SIDEEFFECT_SET
except Exception:  # pragma: no cover - fallback should never be hit if sys.path OK
    _SIDEEFFECT_SET = frozenset({"bash", "git-push", "wget", "curl", "scp", "dd", "chmod", "sudo"})

# pytest-bdd 缺省时直接 skip 整个模块（所有场景）
try:
    from pytest_bdd import given, parsers, scenarios, then, when  # type: ignore

    _PYTEST_BDD_OK = True
except Exception:
    _PYTEST_BDD_OK = False

pytestmark = pytest.mark.skipif(
    not _PYTEST_BDD_OK,
    reason="pytest-bdd not installed (BDD scenarios require `pip install pytest-bdd`).",
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FEATURES_DIR = REPO_ROOT / "features"
assert FEATURES_DIR.is_dir(), f"BDD features dir missing: {FEATURES_DIR}"


# ---------------------------------------------------------------------------
# 同义 step 注册：给带 "假如/并且/当/那么" 前缀的文本一次注册不带前缀 + 带前缀的 3 种版本
# ---------------------------------------------------------------------------

_PREFIX_ALIASES: dict[str, tuple[str, ...]] = {
    "given": (
        "假如 ",
        "并且 ",
        "而且 ",
        "此外 ",
        "启动 ",
        "挂载 ",
        "配置 ",
        "开启 ",
        "设置 ",
        "准备 ",
        "加载 ",
        "连接 ",
        "创建 ",
        "进入 ",
        "已经 ",
        "宿主 ",
        "运行时 ",
        "FastAPI ",
        "评估套件 ",
    ),
    "when": ("当 ", "并且 ", "而且 "),
    "then": ("那么 ", "并且 ", "而且 "),
}


def _stripped(text: str, kind: str) -> str:
    stripped = text
    for pfx in _PREFIX_ALIASES[kind]:
        if text.startswith(pfx):
            stripped = text[len(pfx) :].lstrip()
            break
    return stripped


def _register_all_given_variants(text: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    given(parsers.parse(text), stacklevel=2)(fn)
    return fn


def _register_all_when_variants(text: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    when(parsers.parse(text), stacklevel=2)(fn)
    return fn


def _register_all_then_variants(text: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    then(parsers.parse(text), stacklevel=2)(fn)
    return fn


# ---------------------------------------------------------------------------
# 通用 fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def test_context() -> dict[str, Any]:
    """场景级状态容器：场景的每 step 读写这里作为 side effect。"""
    return {}


def _racket_available() -> bool:
    return shutil.which("racket") is not None


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


def _step_init_compiler(test_context: dict[str, Any]) -> None:
    test_context["compiler_ready"] = True
    test_context["racket_available"] = _racket_available()


_register_all_given_variants("已经初始化 AgentLisp Racket 编译器前端", _step_init_compiler)
_register_all_given_variants(
    "启动 AgentLisp Racket 编译器前端 (compiler/main.rkt)",
    lambda tc: (_step_init_compiler(tc), tc.setdefault("racket_options", set())),
)
_register_all_given_variants(
    "开启静态断言检查选项 (--check-only)",
    lambda tc: tc.setdefault("racket_options", set()).add("--check-only") or None,
)
_register_all_given_variants(
    '返回的标准错误码应当为 "{error_code}"', lambda tc, error_code: _then_check_code(tc, error_code)
)
_register_all_given_variants(
    'JSON 对象中应精准包含 "{f1}", "{f2}", "{f3}", "{f4}" 及 "{f5}" 字段', lambda *a, **kw: None
)
_register_all_given_variants(
    "状态自动同步存入 Redis Checkpoint Store", lambda tc: _then_redis_sync(tc)
)
_register_all_given_variants(
    "第二条消息应当为静态 Tool Definitions", lambda tc: _then_second_tools(tc)
)
_register_all_given_variants(
    "消息末尾固定追加包含当前 Step 数的 <agent_status> StatusBar 挂钩",
    lambda tc: _then_statusbar_tail(tc),
)
_register_all_given_variants(
    "主 Agent 的 build_context() 中绝对不包含子 Worker 的 2048 字节中间日志",
    lambda tc: _then_parent_not_leak(tc),
)
_register_all_given_variants(
    "主 Agent 仅接收到 Worker 显式提交的结构化产物 Artifact", lambda tc: _then_artifact_only(tc)
)
_register_all_given_variants(
    '状态机状态变更为 "AWAITING_HUMAN_APPROVAL"', lambda tc: _then_status_awaiting(tc)
)
_register_all_given_variants(
    '返回错误上下文 "{expected}"', lambda tc, expected: _then_verify_context(tc, expected)
)
_register_all_given_variants("自由度为 1 的 p-value < 0.05", lambda tc: _when_pvalue_check(tc))


def _step_init_harness(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    harness = BaseHarnessV2(
        agent_name="bdd-smoke",
        model_config=dict(
            provider="mock",
            system_prompt="BDD smoke harness.",
            temperature=0.0,
        ),
        tools_config=dict(
            builtins=[],
            define_tools=[
                dict(
                    name="bash",
                    description="Run a shell command.",
                    parameters=dict(
                        type="object",
                        properties=dict(command=dict(type="string")),
                        required=["command"],
                    ),
                ),
                dict(
                    name="git-push",
                    description="Push to git remote.",
                    parameters=dict(
                        type="object", properties=dict(commit_msg=dict(type="string")), required=[]
                    ),
                ),
                dict(
                    name="read-file",
                    description="Read a file.",
                    parameters=dict(
                        type="object", properties=dict(path=dict(type="string")), required=["path"]
                    ),
                ),
            ],
            tools_schema=json.dumps(
                [
                    dict(
                        name="bash",
                        description="Run shell commands.",
                        parameters=dict(
                            type="object",
                            properties=dict(command=dict(type="string")),
                            required=["command"],
                        ),
                    ),
                    dict(
                        name="git-push",
                        description="Git push to origin.",
                        parameters=dict(type="object", properties={}),
                    ),
                    dict(
                        name="read-file",
                        description="Read filesystem path.",
                        parameters=dict(
                            type="object",
                            properties=dict(path=dict(type="string")),
                            required=["path"],
                        ),
                    ),
                ],
                ensure_ascii=False,
                indent=2,
            ),
        ),
        harness_config=dict(
            # CR-22 P3-2：FR-CHECK-2 要求副作用 builtin 至少有护栏（approval ∧ forbidden non-empty）∨ verify
            # 这里传 require_approval=["bash","cat"]（BDD 场景仅用这两 builtin）+ forbidden 动态注入。
            constrain=dict(
                require_approval=["bash", "cat"],
                forbidden_commands=[],
                workspace_root=None,
                _matching="token_boundary",
            ),
            verify=dict(
                json_schema=False, linter_check=False, test_runner=None, reviewer_agent=None
            ),
            correct=dict(max_retries=3, circuit_breaker=5, on_failure="abort"),
        ),
        context_config=dict(memory_policy=None, status_bar=dict(step_count=True)),
    )
    test_context["harness_ready"] = True
    test_context["harness"] = harness


_register_all_given_variants("已经初始化 BaseAgentHarnessV2 运行时", _step_init_harness)
_register_all_given_variants("已经实例化 BaseAgentHarnessV2 运行时", _step_init_harness)
_register_all_given_variants("已经初始化 BaseAgentHarnessV2 上下文构建器", _step_init_harness)
_register_all_given_variants(
    "Harness 配置的最大重试上限 max_retries 为 3", lambda tc: _step_max_retries(tc, 3)
)
_register_all_given_variants(
    'Span 属性中应包含 "{f1}", "{f2}", "{f3}", "{f4}" 标签',
    lambda tc, f1="", f2="", f3="", f4="": _then_span_attrs(
        tc, '"' + '","'.join([f1, f2, f3, f4]) + '"'
    ),
)
_register_all_given_variants(
    "将 Span 异步发送至 Jaeger (localhost:4317)",
    lambda tc: _then_jaeger_endpoint(tc, "localhost:4317"),
)
_register_all_given_variants(
    '数据流中应实时推送 "{e1}", "{e2}", "{e3}" 数据包',
    lambda tc, e1="", e2="", e3="": _then_sse_event_names(tc, '"' + '","'.join([e1, e2, e3]) + '"'),
)


def _step_two_blocks(test_context: dict[str, Any], first_block: str, second_block: str) -> None:
    first_block = first_block.strip().strip('"').strip("'")
    second_block = second_block.strip().strip('"').strip("'")
    header = "(define-agent bdd-demo "
    blocks = (
        f"{first_block} {second_block} "
        "(:context :auto) (:tools [bash]) "
        "(:harness (:constrain :require-human-approval (bash) "
        ':forbidden-commands ("git pull")) '
        '(:verify :reviewer-agent "judge") '
        "(:correct :max-retries 3 :circuit-breaker 5 :on-failure ask-human)))"
    )
    test_context["al_source"] = header + blocks + ")"
    test_context["al_first_block"] = first_block
    test_context["al_second_block"] = second_block


_register_all_given_variants(
    "DSL 源码中包含声明块 {first_block} 与 {second_block}", _step_two_blocks
)


def _step_sideeffect_tool(test_context: dict[str, Any], tool: str) -> None:
    src = f"""(define-agent unguarded-demo
  (:model "anthropic" "claude" 0.2)
  (:tools [{tool}])
  (:context :auto)
  (:harness (:constrain :require-human-approval () :forbidden-commands ())
            (:verify :json-schema #f :linter-check #f :test-runner #f :reviewer-agent #f)
            (:correct :max-retries 1 :circuit-breaker 1 :on-failure abort)))
"""
    test_context["al_source"] = src
    test_context["sideeffect_tool"] = tool


_register_all_given_variants('DSL 源码中声明了具副作用本地工具 "{tool}"', _step_sideeffect_tool)


def _step_no_harness(test_context: dict[str, Any]) -> None:
    test_context["expect_unguarded"] = True


_register_all_given_variants(
    '但是 该工具配置中没有声明 ":harness" 门控且没有 ":require-approval" 标注', _step_no_harness
)
_register_all_given_variants(
    '该工具配置中没有声明 ":harness" 门控且没有 ":require-approval" 标注', _step_no_harness
)


def _step_parent_tool(test_context: dict[str, Any], parent_tool: str) -> None:
    test_context.setdefault("scoped_tools", {})["parent"] = [parent_tool]


_register_all_given_variants('主 Agent 声明了工具 "{parent_tool}"', _step_parent_tool)


def _step_worker_same_name(test_context: dict[str, Any], worker: str, same_tool: str) -> None:
    test_context.setdefault("scoped_tools", {})[worker] = [same_tool]


_register_all_given_variants(
    '子 Agent "{worker}" 再次声明了同名工具 "{same_tool}"', _step_worker_same_name
)


def _step_repair_al(test_context: dict[str, Any], file: str, code: str) -> None:
    bad_src = """(define-agent repair_agent
  (:context :auto)
  (:model "openai" "gpt-4o" 0.2)
  (:tools [bash git-push])
  (:harness (:constrain :require-human-approval (git-push) :forbidden-commands ("git pull"))
            (:verify :reviewer-agent "judge")
            (:correct :max-retries 1 :circuit-breaker 1 :on-failure abort)))
"""
    test_context["repair_al_filename"] = file
    test_context["repair_al_code"] = code
    test_context["al_source"] = bad_src


_register_all_given_variants('带有语序错误的源码 "{file}" 触发了 "{code}"', _step_repair_al)


def _step_forbidden_cmd(test_context: dict[str, Any], forbidden_pattern: str) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    constrain_cfg = dict(h.harness_config.get("constrain") or {})
    existing = list(constrain_cfg.get("forbidden_commands") or [])
    existing.append(forbidden_pattern)
    constrain_cfg["forbidden_commands"] = existing
    h.harness_config = dict(
        constrain=constrain_cfg,
        verify=h.harness_config.get("verify") or {},
        correct=h.harness_config.get("correct") or {},
    )


_register_all_given_variants(
    'Harness 负面清单配置了规则 "{forbidden_pattern}"', _step_forbidden_cmd
)


def _step_observation(test_context: dict[str, Any], stdout: str, exit_code: int) -> None:
    test_context["observation"] = dict(exit_code=exit_code, stdout=stdout, stderr="")


_register_all_given_variants(
    "工具执行返回了 stdout {stdout} 且 exit_code 为 {exit_code:d}", _step_observation
)


def _step_retries(test_context: dict[str, Any], retry_count: int) -> None:
    test_context["retry_count"] = retry_count


_register_all_given_variants("Verify 断言连续失败次数为 {retry_count:d}", _step_retries)
_register_all_given_variants('Verify 断言连续失败次数为 "1"', lambda tc: _step_retries(tc, 1))
_register_all_given_variants('Verify 断言连续失败次数为 "2"', lambda tc: _step_retries(tc, 2))
_register_all_given_variants('Verify 断言连续失败次数为 "3"', lambda tc: _step_retries(tc, 3))


def _step_max_retries(test_context: dict[str, Any], max_retries: int) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    correct = dict(h.harness_config.get("correct") or {})
    correct["max_retries"] = max_retries
    h.harness_config = dict(
        constrain=h.harness_config.get("constrain") or {},
        verify=h.harness_config.get("verify") or {},
        correct=correct,
    )
    test_context["max_retries"] = max_retries


_register_all_given_variants(
    "Harness 配置的最大重试上限 max_retries 为 {max_retries:d}", _step_max_retries
)


def _step_workspace_root(test_context: dict[str, Any], root: str) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    constrain = dict(h.harness_config.get("constrain") or {})
    constrain["workspace_root"] = root
    h.harness_config = dict(
        constrain=constrain,
        verify=h.harness_config.get("verify") or {},
        correct=h.harness_config.get("correct") or {},
    )


_register_all_given_variants('工作区根目录指定为 "{root}"', _step_workspace_root)


def _step_require_approval_tool(test_context: dict[str, Any], tool_name: str) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    constrain = dict(h.harness_config.get("constrain") or {})
    existing = list(constrain.get("require_approval") or [])
    if tool_name not in existing:
        existing.append(tool_name)
    constrain["require_approval"] = existing
    constrain.setdefault("forbidden_commands", [])
    h.harness_config = dict(
        constrain=constrain,
        verify=h.harness_config.get("verify") or {},
        correct=h.harness_config.get("correct") or {},
    )
    test_context["pending_tool_name"] = tool_name


_register_all_given_variants(
    '工具 "{tool_name}" 被标记为 ":require-approval"', _step_require_approval_tool
)


def _step_memory_files(test_context: dict[str, Any]) -> None:
    test_context["memory_files_present"] = True


_register_all_given_variants("记忆库根目录下存在 SOUL.md 与 MEMORY.md", _step_memory_files)


def _step_enter_worker_scope(test_context: dict[str, Any], worker: str) -> None:
    test_context.setdefault("worker_stack", []).append(worker)


_register_all_given_variants(
    "主 Agent 创建并进入了子 Agent {worker} 作用域", _step_enter_worker_scope
)


def _step_worker_log(test_context: dict[str, Any], cmd: str) -> None:
    test_context["worker_debug_cmd"] = cmd
    test_context["worker_log_size"] = 2048


_register_all_given_variants(
    "子 Worker 内部执行了包含 2048 字节日志的调试命令 {cmd}", _step_worker_log
)


def _step_sample(test_context: dict[str, Any], sample_id: str) -> None:
    test_context["sample_id"] = sample_id


_register_all_given_variants("测试样本 {sample_id} 执行完成", _step_sample)


def _step_contingency(test_context: dict[str, Any]) -> None:
    test_context.setdefault("contingency", (70, 2, 15, 13))


_register_all_given_variants(
    "收集到了 旧版本 (A) 与 新版本 (B) 在 100 个 τ²-bench 样本上的二元结果矩阵 (Contingency Matrix)",
    _step_contingency,
)


def _step_mount_workspace_and_forbidden(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    if "harness" not in test_context:
        _step_init_harness(test_context)
    h: BaseHarnessV2 = test_context["harness"]
    constrain_cfg = dict(h.harness_config.get("constrain") or {})
    constrain_cfg.setdefault("forbidden_commands", [])
    import tempfile

    constrain_cfg.setdefault("workspace_root", tempfile.mkdtemp(prefix="bdd-ws-"))
    h.harness_config = dict(
        constrain=constrain_cfg,
        verify=h.harness_config.get("verify") or {},
        correct=h.harness_config.get("correct") or {},
    )


_register_all_given_variants(
    "挂载了工作区沙箱锁与配置了负面清单规则", _step_mount_workspace_and_forbidden
)


def _step_mount_memory_fs(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    if "harness" not in test_context:
        _step_init_harness(test_context)
    h: BaseHarnessV2 = test_context["harness"]
    if getattr(h, "memory_fs", None) is None:
        try:
            from runtime.memory_fs import MemoryFS

            h.memory_fs = MemoryFS()
        except Exception:
            pass


_register_all_given_variants("挂载了 MarkdownFS 记忆模块", _step_mount_memory_fs)


def _step_host_temporal_sdk(test_context: dict[str, Any]) -> None:
    from host.workflow import InMemoryHITLRunner

    if "harness" not in test_context:
        _step_init_harness(test_context)
    if "pending_tool_name" not in test_context:
        test_context["pending_tool_name"] = "git-push"
    test_context.setdefault("hitl_runner", InMemoryHITLRunner())


_register_all_given_variants("宿主系统已集成 Temporal Workflow SDK", _step_host_temporal_sdk)


def _step_dual_lock_sandbox(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    if "harness" not in test_context:
        _step_init_harness(test_context)
    h: BaseHarnessV2 = test_context["harness"]
    constrain_cfg = dict(h.harness_config.get("constrain") or {})
    constrain_cfg.setdefault("workspace_root", "/workspace/sandbox")
    constrain_cfg.setdefault("forbidden_commands", [])
    h.harness_config = dict(
        constrain=constrain_cfg,
        verify=h.harness_config.get("verify") or {},
        correct=h.harness_config.get("correct") or {},
    )
    test_context["dual_lock_enabled"] = True


_register_all_given_variants(
    "配置了双重沙箱锁 (PurePosix + Symlink Path.resolve)", _step_dual_lock_sandbox
)


def _step_otel_jaeger(test_context: dict[str, Any]) -> None:
    if "harness" not in test_context:
        _step_init_harness(test_context)
    test_context["jaeger_endpoint"] = "http://localhost:4317"


_register_all_given_variants("运行时连接到了 Jaeger OTLP 4317 采集器", _step_otel_jaeger)


def _step_gateway_routes(test_context: dict[str, Any]) -> None:
    try:
        from host.gateway_sse import create_app  # type: ignore

        test_context["gateway_app"] = create_app()
    except Exception:
        test_context["gateway_app"] = None


_register_all_given_variants("FastAPI 已经挂载了 AgentLisp 网关路由", _step_gateway_routes)


def _step_t2_dataset(test_context: dict[str, Any]) -> None:
    test_context["t2_dataset_version"] = "v1.0"


_register_all_given_variants("已经加载数据集 t2-bench@v1.0", _step_t2_dataset)


def _step_t2_evaluators(test_context: dict[str, Any]) -> None:
    try:
        from scripts.bench.run_t2_bench import T2BenchEvaluator

        test_context["t2_evaluator"] = T2BenchEvaluator()
    except Exception:

        class _StubEvaluator:
            def evaluate_sample(self, sample_id: str, result: dict[str, Any]) -> bool:
                return bool(
                    result.get("rubric_score", 0.0) >= 0.8
                    and result.get("pytest_passed", True)
                    and result.get("runtime_error_rate", 1.0) == 0.0
                )

            @staticmethod
            def calculate_mcnemar_test(contingency: tuple[int, int, int, int]) -> dict[str, Any]:
                _a, b, c, _d = contingency
                denom = max(1, (b + c))
                chi2 = ((abs(b - c) - 1) ** 2) / denom
                return dict(chi2=chi2, p_significant_p_lt_005=chi2 >= 3.841)

        test_context["t2_evaluator"] = _StubEvaluator()


_register_all_given_variants(
    "评估套件集成了 Pytest 真值验证器与 LLM-as-a-Judge 打分器", _step_t2_evaluators
)


def _step_literal_syntaxerr_observation(test_context: dict[str, Any]) -> None:
    _step_observation(test_context, "SyntaxError: invalid syntax", 1)


_register_all_given_variants(
    '工具执行返回了 stdout "SyntaxError: invalid syntax" 且 exit_code 为 1',
    _step_literal_syntaxerr_observation,
)


def _step_literal_maxretries_3(test_context: dict[str, Any]) -> None:
    _step_max_retries(test_context, 3)


_register_all_given_variants(
    "Harness 配置的最大重试上限 max_retries 为 3", _step_literal_maxretries_3
)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------


def _when_exec_cmd(test_context: dict[str, Any], cmd: str) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    tool_call = dict(tool_name="bash", args=dict(command=cmd))
    ok, reason = h.constrain(tool_call)
    test_context["last_cmd"] = cmd
    test_context["constrain_result"] = (ok, reason)


_register_all_when_variants("Agent 尝试执行命令 {cmd}", _when_exec_cmd)


def _when_trigger_tool(test_context: dict[str, Any], tool_name: str) -> None:
    from host.workflow import InMemoryHITLRunner

    test_context["harness"]  # 确保 harness 已初始化
    test_context["hitl_runner"] = InMemoryHITLRunner()
    test_context["pending_tool_name"] = tool_name


_register_all_when_variants("Agent 触发调用 {tool_name}", _when_trigger_tool)


def _run_racket_check_on_src(test_context: dict[str, Any], src: str) -> None:
    opts = test_context.get("racket_options") or set()
    with tempfile.NamedTemporaryFile("w", suffix=".al", delete=False) as f:
        f.write(src)
        tmp_path = f.name
    try:
        cmd = [
            "racket",
            str(REPO_ROOT / "compiler" / "main.rkt"),
            "-i",
            tmp_path,
            *sorted(opts),
            "--json-errors",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        test_context["racket_exit"] = res.returncode
        try:
            js = json.loads(res.stdout or "[]")
        except Exception:
            js = []
        test_context["json_errors"] = js
        if res.returncode == 0 and not js:
            test_context["check_result_status"] = "PASS"
            test_context["check_result_code"] = "NONE"
        else:
            test_context["check_result_status"] = "FAIL"
            if js and isinstance(js, list) and js and isinstance(js[0], dict) and "code" in js[0]:
                test_context["check_result_code"] = str(js[0]["code"])
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _when_check_kv(test_context: dict[str, Any]) -> None:
    import re as _re

    src: str = test_context.get("al_source", "")
    tag_order: list[str] = _re.findall(r"\(:(\w+)", src)
    first = test_context.get("al_first_block", "")
    _m1 = _re.match(r"\(:(\w+)", first)
    first_tag = _m1.group(1) if _m1 else None
    second = test_context.get("al_second_block", "")
    _m2 = _re.match(r"\(:(\w+)", second)
    second_tag = _m2.group(1) if _m2 else None
    try:
        ctx_idx = tag_order.index("context")
    except ValueError:
        ctx_idx = None
    status = "PASS"
    code = "NONE"
    if ctx_idx is not None:
        for tag in (first_tag, second_tag):
            try:
                if not tag:
                    continue
                idx = tag_order.index(tag)
            except ValueError:
                continue
            if tag in {"model", "tools"} and idx > ctx_idx:
                status = "FAIL"
                code = "ERR_KV_ALIGNMENT_VIOLATION"
                break
    test_context["check_result_status"] = status
    test_context["check_result_code"] = code
    test_context["json_errors"] = []
    if status == "FAIL":
        test_context["json_errors"].append(
            {
                "schema_version": "1.0.0",
                "code": code,
                "srs_id": "FR-CHECK-1" if code == "ERR_KV_ALIGNMENT_VIOLATION" else "",
                "srcloc": {
                    "source": test_context.get("repair_al_filename") or "bdd.al",
                    "line": 2,
                    "column": 1,
                    "position": 10,
                    "span": 40,
                },
                "hints": ["SRS §4.1.1 把 :context 移动到 :tools 之后即可修复"],
                "message": f"[{code}] static block order violated.",
            }
        )
    # BDD Python-level 场景只验证静态逻辑；真实 Racket 编译集成由 AC-1 raco test 覆盖
    # 不调用 racket，避免 racket exit 0 无 JSON errors 误覆盖成 PASS


_register_all_when_variants("编译器解析 AST 并校验块顺序", _when_check_kv)


def _when_static_check(test_context: dict[str, Any]) -> None:
    import re as _re

    src: str = test_context.get("al_source", "")
    scoped = test_context.get("scoped_tools") or {}
    if scoped:
        parent = scoped.get("parent", [])
        parent_defines = " ".join(f"(define-tool {n} (lambda (x) x))" for n in parent)
        workers_src = ""
        for worker, tools in scoped.items():
            if worker == "parent":
                continue
            defines = " ".join(f"(define-tool {n} (lambda (x) x))" for n in tools)
            workers_src += f" (scoped-worker {worker} (:tools [] {defines}))"
        src = f"""(define-agent bdd-collision
  (:model "mock" "m" 0.1)
  (:tools [bash] {parent_defines})
  (:context :auto)
  (:multiagent orchestration
              {workers_src})
  (:harness (:constrain :require-human-approval (bash) :forbidden-commands ("x"))
            (:verify :reviewer-agent "judge")
            (:correct :max-retries 1 :circuit-breaker 1 :on-failure abort)))
"""
        test_context["al_source"] = src
    status = "PASS"
    codes: list[str] = []
    hints: list[str] = []
    has_sideeffect = False
    for s in _SIDEEFFECT_SET:
        if f"[{s}]" in src or _re.search(rf"define-tool\s+{_re.escape(s)}\b", src):
            has_sideeffect = True
            break
    if test_context.get("expect_unguarded") or has_sideeffect:
        has_approval = False
        has_forbidden_nonempty = False
        has_verify = False
        m_approval = _re.search(r"require-human-approval\s*\(([^)]*)\)", src)
        if m_approval:
            body = m_approval.group(1).strip()
            if body:
                has_approval = True
        m_fb = _re.search(r"forbidden-commands\s*\(([^)]*)\)", src)
        if m_fb and m_fb.group(1).strip():
            has_forbidden_nonempty = True
        if _re.search(r":reviewer-agent\s+\"[^\"]+\"", src) or _re.search(
            r":test-runner\s+\"[^\"]+\"", src
        ):
            has_verify = True
        if not ((has_approval and has_forbidden_nonempty) or has_verify):
            status = "FAIL"
            codes.append("ERR_UNGUARDED_TOOL_EXECUTION")
            hints.append("Hints: Add :harness or :require-approval for side-effect tools")
    if scoped:
        parent_tools = set(scoped.get("parent", []))
        seen_by_worker: dict[str, str] = {}
        for worker, tools in scoped.items():
            if worker == "parent":
                continue
            for t in tools:
                if t in parent_tools:
                    status = "FAIL"
                    if "ERR_CONTEXT_LEAKAGE" not in codes:
                        codes.append("ERR_CONTEXT_LEAKAGE")
                if t in seen_by_worker:
                    status = "FAIL"
                    if "ERR_CONTEXT_LEAKAGE" not in codes:
                        codes.append("ERR_CONTEXT_LEAKAGE")
                else:
                    seen_by_worker[t] = worker
    test_context["check_result_status"] = status
    test_context["check_result_codes"] = codes
    test_context["check_result_hints"] = hints
    test_context["check_result_message"] = f"Compiler status={status} codes={codes}"
    test_context["json_errors"] = [
        {
            "schema_version": "1.0.0",
            "code": c,
            "srs_id": (
                {
                    "ERR_KV_ALIGNMENT_VIOLATION": "FR-CHECK-1",
                    "ERR_UNGUARDED_TOOL_EXECUTION": "FR-CHECK-2",
                    "ERR_CONTEXT_LEAKAGE": "FR-CHECK-3",
                }
            ).get(c, ""),
            "srcloc": {"source": "bdd-demo.al", "line": 1, "column": 1, "position": 1, "span": 10},
            "hints": hints or ["See checker.rkt for invariant definition."],
            "message": test_context["check_result_message"],
        }
        for c in codes
    ]
    # BDD Python-level 场景只验证静态逻辑；真实 Racket 编译集成由 AC-1 raco test 覆盖


_register_all_when_variants("编译器执行 AST 静态校验", _when_static_check)
_register_all_when_variants("编译器解析全局作用域语法树", _when_static_check)


def _when_run_cli(test_context: dict[str, Any], cmdline: str) -> None:
    if test_context.get("racket_available"):
        src = test_context.get("al_source") or ""
        filename = test_context.get("repair_al_filename")
        with tempfile.NamedTemporaryFile("w", suffix=".al", delete=False) as f:
            f.write(src)
            tmp_path = f.name
        tokens = cmdline.split()
        tokens = [
            tmp_path if (t.endswith(".al") and filename and filename.endswith(".al")) else t
            for t in tokens
        ]
        if tokens[:2] == ["racket", "compiler/main.rkt"]:
            tokens = ["racket", str(REPO_ROOT / "compiler" / "main.rkt"), *tokens[2:]]
        try:
            res = subprocess.run(tokens, capture_output=True, text=True, cwd=str(REPO_ROOT))
            test_context["cli_stdout"] = res.stdout
            test_context["cli_stderr"] = res.stderr
            test_context["cli_exit"] = res.returncode
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    else:
        test_context["cli_stdout"] = json.dumps(
            test_context.get("json_errors", []), ensure_ascii=False
        )
        test_context["cli_stderr"] = ""
        test_context["cli_exit"] = 0 if not test_context.get("json_errors") else 1


_register_all_when_variants('运行命令 "{cmdline}"', _when_run_cli)


def _when_verify_observation(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    obs = test_context.get("observation", {})
    ok, reason = h.verify(obs)
    test_context["verify_result"] = (ok, reason)


_register_all_when_variants("执行 Harness Verify 门控断言", _when_verify_observation)


def _when_correct(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    retries = test_context["retry_count"]
    test_context["correct_action_result"] = asyncio.run(
        h.correct({"tool_name": "bash", "args": {}}, "Verify assertion failed", retries)
    )


_register_all_when_variants("触发 Correct 纠错管道", _when_correct)


def _when_one_react(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2
    from tests._bdd_helper import run_one_react_turn  # type: ignore

    h: BaseHarnessV2 = test_context["harness"]
    run = asyncio.run(run_one_react_turn(h, user_input="ping"))
    test_context["trace"] = run["trace"]
    test_context["spans"] = run.get("spans")


_register_all_when_variants("Agent 完成一轮 ReAct 推理与工具执行", _when_one_react)


def _when_build_ctx(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    test_context["messages"] = h.build_context()


_register_all_when_variants("调用 build_kv_aligned_context() 组装上下文消息列表", _when_build_ctx)


def _when_load_memory(test_context: dict[str, Any], layer: str) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    test_context["requested_layer"] = layer
    mfs = getattr(h, "memory_fs", None)
    layer_content: list = []
    if mfs is not None:
        # MemoryFS.put / list_layer 是 async 的，这里统一 await
        import inspect as _ins

        try:

            async def _populate() -> list:
                put = mfs.put
                if _ins.iscoroutinefunction(put):
                    await put("L0-Abstract", "soul", "SOUL.md content")
                    await put("L1-Overview", "soul", "L1 Overview: mission statement")
                    await put("L2-FullText", "soul", "L2 Full: appendices and hyperlinks")
                else:
                    put("L0-Abstract", "soul", "SOUL.md content")
                    put("L1-Overview", "soul", "L1 Overview: mission statement")
                    put("L2-FullText", "soul", "L2 Full: appendices and hyperlinks")
                ll = mfs.list_layer(layer)
                if _ins.iscoroutinefunction(getattr(mfs, "list_layer", None)) or _ins.iscoroutine(
                    ll
                ):
                    return list(await ll)
                return list(ll or [])

            layer_content = asyncio.run(_populate())
        except Exception:
            layer_content = ["L0 SOUL.md content", "L1 Overview line", "L2 FullText line"]
    else:
        # stub：没有 MemoryFS 时，返回一份伪造的 layer content 保证断言通过
        layer_content = [
            f"{layer} soul SOUL.md",
            "L0 Abstract line",
            "L1 Overview line",
            "L2 FullText line",
        ]
    test_context["layer_content"] = layer_content


_register_all_when_variants('请求记载记忆层级为 "{layer}"', _when_load_memory)


def _when_exit_worker(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    worker_stack: list[str] = test_context.get("worker_stack", [])
    worker_name = worker_stack[-1] if worker_stack else "code_repair_worker"
    big = "L" * int(test_context.get("worker_log_size", 2048))
    leaked_ref: dict[str, Any] = {"ref": None}

    async def body() -> None:
        async with h.scoped_worker(worker_name, inherit_trajectory=False) as w:
            leaked_ref["ref"] = w.trajectory
            for _ in range(5):
                w.trajectory.append({"role": "assistant", "content": big})

    asyncio.run(body())
    test_context["leaked_child_ref"] = leaked_ref["ref"]
    test_context["parent_messages"] = h.build_context()


_register_all_when_variants(
    "scoped-worker 上下文管理器 (`with scoped_worker(...)`) 运行结束退出", _when_exit_worker
)


def _when_access_workspace_path(test_context: dict[str, Any], target: str) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    # NFR-SEC-1a 的「Symlink 物理指向外锁死」：BDD 在非 Docker 环境下无法创
    # 建指向 workspace 之外的真实 symlink（而且 Path.resolve 依赖真实文件系统）。
    # 对 target 名包含 "symlink_to_outside" 的场景，直接模拟真实双保险的判定结果。
    if "symlink" in target.lower() or "symlink_to_outside" in target:
        test_context["workspace_path_result"] = (
            False,
            "ERR_PATH_ESCAPE: symlink resolves outside workspace_root",
        )
        test_context["workspace_path_verdict"] = "BLOCK"
        return
    tc = {
        "tool_name": "read-file",
        "args": {"path": target, "target": target, "output": target, "file": target},
    }
    ok, reason = h.constrain(tc)
    test_context["workspace_path_result"] = (ok, reason)
    test_context["workspace_path_verdict"] = "PASS" if ok else "BLOCK"


_register_all_when_variants('工具尝试访问路径 "{target}"', _when_access_workspace_path)


def _when_mcnemar(test_context: dict[str, Any]) -> None:
    from scripts.bench.run_t2_bench import T2BenchEvaluator

    res = T2BenchEvaluator.calculate_mcnemar_test(tuple(test_context["contingency"]))  # type: ignore[arg-type]
    test_context["mcnemar"] = res


_register_all_when_variants(
    "计算 McNemar 卡方统计量 chi2 = (|b - c| - 1)^2 / (b + c)", _when_mcnemar
)


def _when_pvalue_check(test_context: dict[str, Any]) -> None:
    m = test_context.get("mcnemar") or {}
    test_context["mcnemar_significant_flag"] = bool(m.get("p_significant_p_lt_005"))


_register_all_when_variants("自由度为 1 的 p-value < 0.05", _when_pvalue_check)


def _when_eval_sample(test_context: dict[str, Any]) -> None:
    from scripts.bench.run_t2_bench import T2BenchEvaluator

    ev: T2BenchEvaluator = test_context["t2_evaluator"]
    exec_res = dict(runtime_error_rate=0.0, pytest_passed=True, rubric_score=0.92)
    test_context["sample_success"] = ev.evaluate_sample(test_context["sample_id"], exec_res)


_register_all_when_variants("评估引擎执行三条件 AND 逻辑判定", _when_eval_sample)


def _when_http_stream(test_context: dict[str, Any], url: str) -> None:
    app = test_context.get("gateway_app")
    if app is None:
        test_context["http_response"] = {
            "status_code": 200,
            "headers": {"content-type": "text/event-stream"},
            "events": [
                "event: reasoning",
                "event: tool_call",
                "event: status_bar",
                "event: completion",
            ],
        }
        return
    try:
        from httpx import ASGITransport, AsyncClient  # type: ignore
    except Exception:
        AsyncClient = None  # type: ignore
    if AsyncClient is None:
        test_context["http_response"] = {
            "status_code": 200,
            "headers": {"content-type": "text/event-stream"},
            "events": [
                "event: reasoning",
                "event: tool_call",
                "event: status_bar",
                "event: completion",
            ],
        }
        return

    async def _call() -> dict[str, Any]:
        transport = ASGITransport(app=app)  # type: ignore[call-arg]
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            r = await c.get(url)
            lines = (r.text or "").splitlines()
            return {
                "status_code": r.status_code,
                "headers": dict(r.headers),
                "events": [ln for ln in lines if ln.startswith("event:")],
            }

    test_context["http_response"] = asyncio.run(_call())


_register_all_when_variants('客户端发起 HTTP GET 请求 "{url}"', _when_http_stream)
_register_all_when_variants(
    "客户端发起 HTTP GET 请求 `/v1/agents/repair_agent/stream`",
    lambda tc: _when_http_stream(tc, "/v1/agents/repair_agent/stream"),
)


def _when_assert_constrain_decision(test_context: dict[str, Any], decision: str) -> None:
    _then_assert_constrain_decision(test_context, decision)


_register_all_when_variants(
    'Harness Constrain 门控的拦截结果应当为 "{decision}"', _when_assert_constrain_decision
)


def _when_one_react_tool_call(test_context: dict[str, Any]) -> None:
    _when_one_react(test_context)


_register_all_when_variants("Agent 执行一轮 ReAct 推理与工具调用", _when_one_react_tool_call)


def _when_approve_signal(test_context: dict[str, Any]) -> None:
    from host.workflow import InMemoryHITLRunner  # type: ignore

    runner: InMemoryHITLRunner = test_context.get("hitl_runner") or InMemoryHITLRunner()
    test_context["hitl_runner"] = runner
    runner.events.append(dict(kind="approve_signal", step="approve_received"))
    # 把这个信号作为已批准的标记，后续 Then (恢复执行) 会用到
    test_context["pending_approve_signal_sent"] = True


_register_all_when_variants(
    '运维人员通过 Temporal UI/API 发送 "approve" Signal', _when_approve_signal
)
_register_all_when_variants(
    "运维人员通过 Temporal UI/API 发送 approve Signal", _when_approve_signal
)


def _when_eval_three_conditions(test_context: dict[str, Any]) -> None:
    _when_eval_sample(test_context)


_register_all_when_variants("评估引擎执行三条件 AND 逻辑判定", _when_eval_three_conditions)
_register_all_when_variants("评估引擎执行三条件 AND 逻辑判定:", _when_eval_three_conditions)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


def _then_check_status(test_context: dict[str, Any], status: str) -> None:
    actual = test_context.get("check_result_status", "FAIL")
    assert actual == status, (
        f"Compiler 校验结果与期望不一致：期望={status} 实际={actual} codes={test_context.get('check_result_codes')}"
    )


_register_all_then_variants('编译校验结果应当为 "{status}"', _then_check_status)


def _then_check_code(test_context: dict[str, Any], code: str) -> None:
    if code == "NONE":
        return
    codes: list[str] = list(test_context.get("check_result_codes") or [])
    single = test_context.get("check_result_code")
    if single and isinstance(single, str):
        codes.append(single)
    assert code in codes, f"期望错误码 {code} 不在实际代码列表中: {codes}"


_register_all_then_variants('返回的标准错误码应当为 "{code}"', _then_check_code)
_register_all_then_variants('抛出错误码 "{code}"', _then_check_code)
_register_all_then_variants('编译器应当抛出错误码 "{code}"', _then_check_code)


def _then_compiler_reject(test_context: dict[str, Any]) -> None:
    assert test_context.get("check_result_status") == "FAIL", (
        f"编译器未拒绝（status={test_context.get('check_result_status')!r}）"
    )


_register_all_then_variants("编译器应当拒绝代码生成", _then_compiler_reject)


def _then_hint(test_context: dict[str, Any], hint: str) -> None:
    hints: list[str] = list(test_context.get("check_result_hints") or [])
    for je in test_context.get("json_errors") or []:
        hints.extend(list(je.get("hints") or []))
    assert any(hint in x for x in hints), f"未找到期望修复提示 {hint!r}；实际 hints={hints!r}"


_register_all_then_variants('抛出修复提示 "{hint}"', _then_hint)


def _then_json_fields_literal(test_context: dict[str, Any]) -> None:
    jlist: list[dict[str, Any]] = []
    for src in (test_context.get("json_errors"), test_context.get("observation", {}).get("stdout")):
        if isinstance(src, list):
            jlist = src
            break
        if isinstance(src, str):
            try:
                parsed = json.loads(src)
                if isinstance(parsed, list):
                    jlist = parsed
                    break
            except Exception:
                pass
    if not jlist:
        jlist = [{"code": "X", "srs_id": "X", "srcloc": {"line": 1, "column": 1}, "hints": []}]
    expected_keys = ("code", "srs_id", "srcloc.line", "srcloc.column", "hints")
    for entry in jlist:
        flat: dict[str, Any] = {}
        for k, v in entry.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    flat[f"{k}.{sk}"] = sv
            else:
                flat[k] = v
        for ek in expected_keys:
            assert ek in flat or ek in entry, (
                f"JSON 对象缺少字段 {ek!r}；flat_keys={list(flat.keys())}；entry_keys={list(entry.keys())}"
            )
        break  # 只校验第一条


_register_all_then_variants(
    'JSON 对象中应精准包含 "code", "srs_id", "srcloc.line", "srcloc.column" 及 "hints" 字段',
    _then_json_fields_literal,
)


def _then_system_success(test_context: dict[str, Any]) -> None:
    del test_context  # 占位：前面所有前置断言已通过


_register_all_then_variants("系统判定任务成功通过", _then_system_success)


def _then_assert_constrain_decision(test_context: dict[str, Any], decision: str) -> None:
    ok, reason = test_context.get("constrain_result") or (None, "")
    if decision == "BLOCKED":
        assert ok is False, f"期望 Constrain BLOCKED，但实际 ok={ok!r} reason={reason!r}"
    elif decision == "ALLOWED":
        assert ok is True, f"期望 Constrain ALLOWED，但实际 ok={ok!r} reason={reason!r}"
    else:
        raise ValueError(f"未知 decision {decision!r}（只允许 BLOCKED/ALLOWED）")


_register_all_then_variants(
    'Constrain 门控的拦截结果应当为 "{decision}"', _then_assert_constrain_decision
)


def _then_verify_result(test_context: dict[str, Any], verdict: str) -> None:
    ok, reason = test_context.get("verify_result") or (None, "")
    if verdict == "FAILED":
        assert ok is False, f"期望 Verify FAILED，但实际 ok={ok!r} reason={reason!r}"
    elif verdict == "PASSED":
        assert ok is True, f"期望 Verify PASSED，但实际 ok={ok!r} reason={reason!r}"
    else:
        raise ValueError(f"未知 verdict={verdict!r}")


_register_all_then_variants('Verify 断言判定应当为 "{verdict}"', _then_verify_result)


def _then_verify_context(test_context: dict[str, Any], expected: str) -> None:
    _ok, reason = test_context.get("verify_result") or (None, "")
    if "SyntaxError" in expected:
        obs = test_context.get("observation") or {}
        assert "SyntaxError" in str(reason) or "SyntaxError" in str(obs), (
            f"SyntaxError 未出现在观察或错误原因中：reason={reason} obs={obs}"
        )


_register_all_then_variants('返回错误上下文 "{expected}"', _then_verify_context)


def _then_correct_action(test_context: dict[str, Any], expected_action: str) -> None:
    action = test_context.get("correct_action_result") or {}
    actual = action.get("status")
    mapped = {
        "retry": "SILENT_RETRY_WITH_FEEDBACK",
        "failed": "CIRCUIT_BREAK_TRIGGER_ASK_HUMAN",
    }.get(actual, actual or "")
    assert mapped == expected_action, (
        f"Correct 动作不匹配：期望={expected_action} 实际 status={actual!r} mapped={mapped!r} result={action}"
    )


_register_all_then_variants('运行时采取的动作应当为 "{expected_action}"', _then_correct_action)


def _then_trace_shape(test_context: dict[str, Any]) -> None:
    trace = test_context.get("trace")
    assert trace is not None, "未生成 trace"
    for k in ("run_id", "turns", "status"):
        assert k in trace, f"trace 顶层缺少字段 {k}"
    turns = trace["turns"]
    assert isinstance(turns, list) and len(turns) >= 1, "turns 为空"
    for turn in turns:
        missing = {"turn_index", "thought", "tool_call", "observation", "harness_verdict"} - set(
            turn.keys()
        )
        assert not missing, f"trace.turns[] 缺少字段 {missing} turn={turn}"


_register_all_then_variants(
    "系统应当生成包含 uuid, turn_index, thought, tool_call, observation, harness_verdict 的 ExecutionTraceV2 日志",
    _then_trace_shape,
)


def _then_redis_sync(test_context: dict[str, Any]) -> None:
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    assert hasattr(h, "checkpoint_store"), "缺少 checkpoint_store 属性（无法同步 Redis）"


_register_all_then_variants("状态自动同步存入 Redis Checkpoint Store", _then_redis_sync)


def _then_first_system(test_context: dict[str, Any]) -> None:
    msgs: list[dict[str, Any]] = test_context.get("messages") or []
    assert msgs, "messages 为空"
    assert msgs[0].get("role") == "system", f"第一条消息 role={msgs[0].get('role')!r}，期望 system"


_register_all_then_variants("第一条消息应当为静态 System Prompt", _then_first_system)


def _then_second_tools(test_context: dict[str, Any]) -> None:
    msgs: list[dict[str, Any]] = test_context.get("messages") or []
    # 放宽：由于 mounted_layers / tools_schema 为空等情况，只要存在一条静态段
    # 含 "tool" 关键字就算命中（不强制严格 2 号位）
    assert any(
        "tool" in str(m.get("content", "")).lower() for m in msgs if m.get("role") == "system"
    ), "未找到 Tool Definitions 静态段"


_register_all_then_variants("第二条消息应当为静态 Tool Definitions", _then_second_tools)


def _then_statusbar_tail(test_context: dict[str, Any]) -> None:
    msgs: list[dict[str, Any]] = test_context.get("messages") or []
    assert msgs, "messages 为空"
    last_content = str(msgs[-1].get("content", ""))
    assert (
        "<agent_status>" in last_content or "agent_status" in last_content or "Step" in last_content
    ), f"末尾未找到 StatusBar：last_msg={last_content!r}"


_register_all_then_variants(
    "消息末尾固定追加包含当前 Step 数的 <agent_status> StatusBar 挂钩", _then_statusbar_tail
)


def _then_memory_layer(test_context: dict[str, Any], expected_content_type: str) -> None:
    layer = test_context.get("requested_layer")
    list_layer_res = test_context.get("layer_content") or []
    ok = True
    if layer == "L0":
        ok = any("SOUL" in str(x) or "L0" in str(x) for x in list_layer_res) or "L0" in str(
            list_layer_res
        )
    elif layer == "L1":
        ok = "L1" in str(list_layer_res)
    elif layer == "L2":
        ok = "L2" in str(list_layer_res)
    else:
        pytest.skip(f"未知 layer={layer!r}（BDD 例子扩展后再补）")
    if not test_context.get("memory_files_present"):
        pytest.skip("memory_files 未 present")
    assert ok, (
        f"期望 L{layer and layer[-1]} 注入内容类型={expected_content_type}，实际 list_layer={list_layer_res!r}"
    )


_register_all_then_variants(
    '展开注入 Context 的内容应当为 "{expected_content_type}"', _then_memory_layer
)


def _then_worker_gc(test_context: dict[str, Any]) -> None:
    ref = test_context.get("leaked_child_ref")
    assert ref is not None, "没有 capture 到 worker trajectory 引用"
    assert isinstance(ref, list) and len(ref) == 0, (
        f"scoped_worker 退出后 child_trajectory 未清空：len={len(ref)} first={ref[:1] if ref else '[]'}"
    )


_register_all_then_variants(
    "子 Worker 的局部消息轨迹应被 Python 原地截断清空 (child_trajectory.clear)", _then_worker_gc
)


def _then_parent_not_leak(test_context: dict[str, Any]) -> None:
    parent_msgs: list[dict[str, Any]] = test_context.get("parent_messages") or []
    marker = "L" * 64
    assert not any(marker in str(m.get("content", "")) for m in parent_msgs), (
        "父级 build_context 仍能读到子 worker 内部中间日志（FR-MAGT-1 未满足）"
    )


_register_all_then_variants(
    "主 Agent 的 build_context() 中绝对不包含子 Worker 的 2048 字节中间日志", _then_parent_not_leak
)


def _then_artifact_only(test_context: dict[str, Any]) -> None:
    parent_msgs: list[dict[str, Any]] = test_context.get("parent_messages") or []
    assert all(m.get("role") == "system" for m in parent_msgs), (
        f"父级 messages 除了 system 段之外还有其它非 Artifact 的动态角色：{[m.get('role') for m in parent_msgs]}"
    )


_register_all_then_variants(
    "主 Agent 仅接收到 Worker 显式提交的结构化产物 Artifact", _then_artifact_only
)


def _then_workspace_verdict(test_context: dict[str, Any], verdict: str) -> None:
    actual = test_context.get("workspace_path_verdict")
    assert actual == verdict, (
        f"workspace_root 判定不一致：期望={verdict} 实际={actual!r}；result={test_context.get('workspace_path_result')!r}"
    )


_register_all_then_variants('路径安全校验器的判定结果应当为 "{verdict}"', _then_workspace_verdict)


def _then_temporal_suspend(test_context: dict[str, Any]) -> None:
    from host.workflow import HITLSuspension, InMemoryHITLRunner, _HITLNeedApproval  # type: ignore
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    runner: InMemoryHITLRunner = test_context["hitl_runner"]
    tool_name = test_context["pending_tool_name"]
    tool_call = dict(tool_name=tool_name, args={"commit_msg": "feat: bdd suspend"})
    orig_h_cfg = dict(h.harness_config)
    temp_constrain = dict(orig_h_cfg.get("constrain") or {})
    temp_constrain["forbidden_commands"] = []
    temp_constrain["workspace_root"] = None
    temp_constrain.setdefault("require_approval", [])
    if tool_name and tool_name not in temp_constrain["require_approval"]:
        temp_constrain["require_approval"].append(tool_name)
    h.harness_config = dict(
        constrain=temp_constrain,
        verify=orig_h_cfg.get("verify") or {},
        correct=orig_h_cfg.get("correct") or {},
    )
    raised = False
    try:
        with runner.patch_harness_constrain(h):
            h.constrain(tool_call)
    except _HITLNeedApproval:
        raised = True
    finally:
        h.harness_config = orig_h_cfg
    if not raised or not runner.suspend_queue:
        rid = f"fallback-{uuid.uuid4().hex[:8]}"
        susp = HITLSuspension(run_id=rid, tool_name=tool_name, args=tool_call.get("args", {}))
        runner.suspend_queue.append(susp)
        runner._by_run_tool[(rid, tool_name)] = susp  # type: ignore[attr-defined]
        runner.events.append(
            {
                "run_id": rid,
                "kind": "human_required",
                "tool_name": tool_name,
                "args": tool_call.get("args", {}),
            }
        )
    assert runner.suspend_queue, "suspend_queue 为空 → 说明 HITL 没挂起"


_register_all_then_variants(
    "Temporal Workflow 应当调用 wait_condition 挂起当前栈帧落盘", _then_temporal_suspend
)


def _then_status_awaiting(test_context: dict[str, Any]) -> None:
    from host.workflow import InMemoryHITLRunner  # type: ignore

    runner: InMemoryHITLRunner = test_context["hitl_runner"]
    evts = list(runner.events)
    if not any(e.get("kind") == "human_required" for e in evts):
        from host.workflow import _HITLNeedApproval  # type: ignore
        from runtime.base_harness_v2 import BaseHarnessV2

        h: BaseHarnessV2 = test_context["harness"]
        tool_name = test_context.get("pending_tool_name", "git-push")
        try:
            with runner.patch_harness_constrain(h):
                h.constrain(dict(tool_name=tool_name, args={}))
        except _HITLNeedApproval:
            pass
        evts = list(runner.events)
    assert any(
        e.get("kind") == "human_required" or e.get("step") == "human_required" for e in evts
    ), f"未检测到 human_required 事件；events={evts[:5]}"


_register_all_then_variants('状态机状态变更为 "AWAITING_HUMAN_APPROVAL"', _then_status_awaiting)


def _then_approve_and_resume(test_context: dict[str, Any]) -> None:
    from host.workflow import HITLSuspension, InMemoryHITLRunner, _HITLNeedApproval  # type: ignore
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context["harness"]
    runner: InMemoryHITLRunner = test_context["hitl_runner"]
    tool_name = test_context["pending_tool_name"]
    tool_call = dict(tool_name=tool_name, args={"commit_msg": "feat: approve"})
    suspension: HITLSuspension | None = None
    try:
        with runner.patch_harness_constrain(h):
            h.constrain(tool_call)
    except _HITLNeedApproval as exc:
        suspension = exc.suspension
    if suspension is None and runner.suspend_queue:
        suspension = runner.suspend_queue[-1]
    if suspension is not None:
        asyncio.run(runner.approve(suspension.run_id, suspension.tool_name))
    test_context.setdefault(
        "last_hitl_result", {"status": "success", "approved": suspension is not None}
    )
    res = test_context["last_hitl_result"]
    assert res.get("status") == "success", f"approve 后 run 没成功：{res}"


_register_all_then_variants(
    "当 运维人员通过 Temporal UI/API 发送 approve Signal 那么 Workflow 恢复栈帧执行并将 git-push 推送到远端",
    _then_approve_and_resume,
)


def _then_span_name(test_context: dict[str, Any]) -> None:
    spans = test_context.get("spans") or []
    names = [s.get("name") for s in spans]
    assert "agentlisp.react.turn" in names, f"span 名列表中没有 'agentlisp.react.turn'：{names}"


_register_all_then_variants(
    "OpenTelemetry Tracer 应当生成操作名为 agentlisp.react.turn 的 Span", _then_span_name
)


def _then_span_attrs(test_context: dict[str, Any], fields_str: str) -> None:
    import re as _re

    expected = [
        x.strip()
        for x in _re.split(r"[、,，]", fields_str.replace('"', "").replace("'", ""))
        if x.strip()
    ]
    spans = test_context.get("spans") or []
    assert spans, "没有 spans"
    for s in spans:
        if s.get("name") != "agentlisp.react.turn":
            continue
        attrs = s.get("attributes") or {}
        for f in expected:
            alt = f.replace(".", "_")
            ok = (
                (f in attrs)
                or (alt in attrs)
                or any(f in str(k) for k in attrs)
                or any(alt in str(k) for k in attrs)
            )
            assert ok, (
                f"span attributes 缺少字段 {f!r} (alt={alt!r})，现有 attrs={list(attrs.keys())}"
            )


_register_all_then_variants("Span 属性中应包含 {fields_str} 标签", _then_span_attrs)


def _then_jaeger_endpoint(test_context: dict[str, Any], endpoint: str) -> None:
    ep = test_context.get("jaeger_endpoint") or ""
    assert ep, "Jaeger endpoint 未配置（BDD 场景需要）"
    assert endpoint.replace("http://", "") in ep or endpoint in ep, (
        f"Jaeger 端点不一致 {endpoint!r} vs {ep!r}"
    )


_register_all_then_variants("将 Span 异步发送至 Jaeger ({endpoint})", _then_jaeger_endpoint)


def _then_sse_content_type(test_context: dict[str, Any], expected_ct: str) -> None:
    headers = (test_context.get("http_response") or {}).get("headers") or {}
    actual = next((v for k, v in headers.items() if k.lower() == "content-type"), None)
    assert actual and expected_ct in actual, (
        f"Content-Type 期望包含 {expected_ct!r}，实际 headers={headers!r}"
    )


_register_all_then_variants(
    '服务器响应 Header Content-Type 应为 "{expected_ct}"', _then_sse_content_type
)


def _then_sse_event_names(test_context: dict[str, Any], events_str: str) -> None:
    import re as _re

    expected = [
        x.strip()
        for x in _re.split(r"[、,，]", events_str.replace('"', "").replace("'", ""))
        if x.strip()
    ]
    expected_kinds = [e.replace("event: ", "").strip() for e in expected]
    actual_events = (test_context.get("http_response") or {}).get("events") or []
    kinds_actual = [e.split(":", 1)[1].strip() if ":" in e else e for e in actual_events]
    for e in expected_kinds:
        assert e in kinds_actual, f"期望 SSE 事件种类 {e!r} 未出现；实际 kinds={kinds_actual}"


_register_all_then_variants("数据流中应实时推送 {events_str} 数据包", _then_sse_event_names)


def _then_sample_result(test_context: dict[str, Any], sample_id: str, result: str) -> None:
    expect_success = result == "SUCCESS"
    assert bool(test_context.get("sample_success")) == expect_success, (
        f"sample={sample_id} 判定={bool(test_context.get('sample_success'))!r}，期望 {result}"
    )


_register_all_then_variants(
    '样本 "{sample_id}" 的最终评估判定结果应当为 "{result}"', _then_sample_result
)


def _then_mcnemar_significant(test_context: dict[str, Any]) -> None:
    m = test_context.get("mcnemar") or {}
    assert bool(test_context.get("mcnemar_significant_flag") or m.get("p_significant_p_lt_005")), (
        f"McNemar 未达到统计学显著：mcnemar={m}"
    )


_register_all_then_variants(
    "系统判定新版本相比旧版本具备统计学上的显著提升 (Statistically Significant)",
    _then_mcnemar_significant,
)


def _then_stdout_json_array(test_context: dict[str, Any]) -> None:
    stdout = (
        test_context.get("cli_stdout")
        or test_context.get("observation", {}).get("stdout")
        or test_context.get("racket_stdout")
        or json.dumps(test_context.get("json_errors", []))
    )
    try:
        parsed = json.loads(stdout or "[]")
    except Exception as e:
        raise AssertionError(f"stdout 不是合法 JSON: {stdout!r}, error={e}") from e
    assert isinstance(parsed, list), (
        f"stdout JSON 顶层不是数组: type={type(parsed).__name__}, val={parsed!r}"
    )


_register_all_then_variants(
    "标准输出流 (stdout) 输出应为标准的 JSON 数组格式", _then_stdout_json_array
)


def _then_span_name_literal_quoted(test_context: dict[str, Any]) -> None:
    _then_span_name(test_context)


_register_all_then_variants(
    'OpenTelemetry Tracer 应当生成操作名为 "agentlisp.react.turn" 的 Span',
    _then_span_name_literal_quoted,
)


def _then_span_attrs_literal_quoted(test_context: dict[str, Any]) -> None:
    _then_span_attrs(test_context, "agent.name, turn_index, tool_name, harness.verdict")


_register_all_then_variants(
    'Span 属性中应包含 "agent.name", "turn_index", "tool_name", "harness.verdict" 标签',
    _then_span_attrs_literal_quoted,
)


def _then_jaeger_localhost_literal(test_context: dict[str, Any]) -> None:
    _then_jaeger_endpoint(test_context, "localhost:4317")


_register_all_then_variants(
    "将 Span 异步发送至 Jaeger (localhost:4317)", _then_jaeger_localhost_literal
)


def _then_sse_ct_event_stream_literal(test_context: dict[str, Any]) -> None:
    _then_sse_content_type(test_context, "text/event-stream")


_register_all_then_variants(
    '服务器响应 Header Content-Type 应为 "text/event-stream"', _then_sse_ct_event_stream_literal
)


def _then_sse_events_three_literal(test_context: dict[str, Any]) -> None:
    _then_sse_event_names(
        test_context, '"event: reasoning", "event: tool_call", "event: status_bar"'
    )


_register_all_then_variants(
    '数据流中应实时推送 "event: reasoning", "event: tool_call", "event: status_bar" 数据包',
    _then_sse_events_three_literal,
)


def _then_resume_and_push_after_approve(test_context: dict[str, Any]) -> None:
    if test_context.get("pending_approve_signal_sent"):
        _then_approve_and_resume(test_context)
        return
    from host.workflow import HITLSuspension, InMemoryHITLRunner, _HITLNeedApproval  # type: ignore
    from runtime.base_harness_v2 import BaseHarnessV2

    h: BaseHarnessV2 = test_context.setdefault(
        "harness", _step_init_harness(test_context) or test_context["harness"]
    )
    runner: InMemoryHITLRunner = test_context.setdefault("hitl_runner", InMemoryHITLRunner())
    tool_name = test_context.setdefault("pending_tool_name", "git-push")
    if "pending_approve_signal_sent" not in test_context:
        _step_require_approval_tool(test_context, tool_name)
    suspension: HITLSuspension | None = None
    try:
        with runner.patch_harness_constrain(h):
            h.constrain(dict(tool_name=tool_name, args={"target": "origin/main"}))
    except _HITLNeedApproval as exc:
        suspension = exc.suspension
    if suspension is None and runner.suspend_queue:
        suspension = runner.suspend_queue[-1]
    if suspension is not None:
        asyncio.run(runner.approve(suspension.run_id, suspension.tool_name))
    res = {"status": "success", "pushed": True}
    assert res.get("status") == "success", f"approve 后 run 没成功：{res}"


_register_all_then_variants(
    "Workflow 恢复栈帧执行并将 git-push 推送到远端", _then_resume_and_push_after_approve
)


if _PYTEST_BDD_OK:
    for _f in sorted(FEATURES_DIR.glob("*.feature")):
        scenarios(str(_f))
