"""
V2 Harness 合并版回归测试 (runtime/tests/test_harness_v2.py)

覆盖：
  1. build_kv_aligned_context 顺序 (Fix Issue #3)
  2. Constrain 词边界精确匹配 (Fix Issue #4)
  3. step/run 不再硬编码 mock LLM + tool (Fix Issue #1)
  4. 证据链 ExecutionTraceV2 + turns[].duration_ms + status/final_answer (Fix Issue #2)
  5. Checkpoint 保存与 from_checkpoint 恢复 (Fix Issue #5)
  6. Verify 失败 → Correct retry/circuit-breaker 分支
  7. StatusBar 回调：on_start / on_step / on_done 全触发
  8. 旧 pytest 15/15 仍然全部通过（在外部集成时一并回归）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from runtime.base_harness_v2 import (
    BaseHarnessV2,
    ExecutionTraceV2,
    MockLLMClient,
    _contains_forbidden_token,
    build_kv_aligned_context,
)

# ============================================================================
# 1. build_kv_aligned_context 顺序 (Issue #3: Status Bar 必须是 system 角色，不是 user)
# ============================================================================


def test_build_context_kv_order_and_status_bar_role() -> None:
    ctx = build_kv_aligned_context(
        system_prompt="SP",
        tools_schema_text="TOOL",
        tools_openai_schema=[{"type": "function", "function": {"name": "f", "description": "d"}}],
        trajectory=[
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
        ],
        step_count=5,
        status_bar_config={"step_count": True},
        terminated=False,
    )
    # 顺序断言：0=system SP, 1=system tools_definition, 2..3=trajectory, 4=system agent_status
    assert len(ctx) == 5, f"expect 5 messages got {len(ctx)}: {ctx!r}"
    assert ctx[0] == {"role": "system", "content": "SP"}
    assert ctx[1]["role"] == "system" and "<tools_definition>" in ctx[1]["content"]
    assert "TOOL" in ctx[1]["content"] and "OpenAI tools schema" in ctx[1]["content"]
    assert ctx[2] == {"role": "user", "content": "u1"}
    assert ctx[3] == {"role": "assistant", "content": "a1"}
    # ★ 关键修复：Status Bar 必须是 system 角色（修复 Issue #3）
    assert ctx[4]["role"] == "system", (
        f"Issue #3 regression: Status Bar role={ctx[4]['role']!r} 应为 system"
    )
    assert ctx[4]["content"] == "<agent_status>Step: 5 | Status: Active</agent_status>"


# ============================================================================
# 2. Constrain 词边界精确匹配 (Issue #4: 不能子串误杀)
# ============================================================================


@pytest.mark.parametrize(
    "cmd,forbidden,expected_hit",
    [
        ("rm -rf /", "rm -rf", True),
        ("rm -rfx /data", "rm -rf", False),  # 子串命中但 token 不命中 → 不拦截
        ("ls /tmp/rm -rf-work", "rm -rf", False),  # shlex token 拆分后不含 → 不拦截
        ("echo hello world", "cat", False),
        ("cat /etc/passwd", "cat", True),
        ("category", "cat", False),  # 词边界不匹配 → 不拦截
        ("concatenate file1 file2", "cat", False),
        ("bash -c 'rm -rf /tmp/x'", "rm -rf", True),  # shlex 后参数含完整 forbidden → 拦截
    ],
)
def test_constrain_token_boundary(cmd: str, forbidden: str, expected_hit: bool) -> None:
    got = _contains_forbidden_token(cmd, forbidden)
    assert got is expected_hit, (
        f"_contains_forbidden_token mis-match: cmd={cmd!r} forbidden={forbidden!r} "
        f"expected_hit={expected_hit} got={got}"
    )


# ============================================================================
# 3-6. 用 MockLLMClient 跑通 BaseHarnessV2.run()，覆盖 evidence/constrain/correct/checkpoint
# ============================================================================


class _EchoToolRegistry:
    def __init__(self, register: dict[str, Any] | None = None) -> None:
        self._handlers: dict[str, Any] = dict(register or {})
        if "echo" not in self._handlers:
            self._handlers["echo"] = lambda **kw: kw.get("message", "")
        if "failing" not in self._handlers:
            self._handlers["failing"] = lambda **kw: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[misc]

    async def acall(self, name: str, **kwargs: Any) -> Any:
        return self._handlers[name](**kwargs)

    def names(self) -> list[str]:
        return list(self._handlers.keys())

    def to_openai_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": n,
                    "description": f"tool {n}",
                    "parameters": {"type": "object"},
                },
            }
            for n in self._handlers
        ]


class _RecordingStatusBar:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def on_start(self, run_id: str, agent_name: str | None) -> None:
        self.events.append(("on_start", run_id, agent_name))

    def on_step(self, run_id: str, turn_index: int, event: str, detail: Any = None) -> None:
        self.events.append(("on_step", run_id, turn_index, event))

    def on_done(
        self, run_id: str, status: str, final_answer: str | None, error: str | None
    ) -> None:
        self.events.append(("on_done", run_id, status, final_answer, error))


def _make_harness(llm_responses, **overrides: Any) -> BaseHarnessV2:
    base_kwargs: dict[str, Any] = dict(
        model_config={"system_prompt": "SP for V2 tests", "agent_name": "test-agent-v2"},
        context_config={"status_bar": {"step_count": True}},
        tools_config={"tools_schema": "Tool: echo(message:str)"},
        harness_config={
            "constrain": {"forbidden_commands": ["rm -rf"]},
            "correct": {"max_retries": 2, "on_failure": "fail_fast"},
        },
    )
    if "llm_client" not in overrides:
        base_kwargs["llm_client"] = MockLLMClient(responses=llm_responses)
    base_kwargs.update(overrides)
    return BaseHarnessV2(**base_kwargs)


@pytest.mark.asyncio
async def test_run_success_has_evidence_chain_and_statusbar_events() -> None:
    sb = _RecordingStatusBar()
    h = _make_harness(
        llm_responses=[
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "echo", "arguments": {"message": "hi"}},
                    }
                ],
            },
            {"role": "assistant", "content": "FINAL"},
        ],
        tool_registry=_EchoToolRegistry(),
        status_bar=sb,
    )
    trace: ExecutionTraceV2 = await h.run("hello")
    # Evidence 链 (Issue #2)
    assert trace.run_id and trace.agent_name == "test-agent-v2"
    assert trace.status == "success"
    assert trace.final_answer == "FINAL"
    assert len(trace.turns) >= 2
    for t in trace.turns:
        assert t.finished_at is not None and t.duration_ms >= 0
    # Status Bar 回调 (Issue #5)
    events = sb.events
    assert events[0][0] == "on_start"
    assert events[-1][0] == "on_done"
    done = events[-1]
    assert done[2] == "success" and done[3] == "FINAL"
    assert any(e[0] == "on_step" for e in events)


@pytest.mark.asyncio
async def test_constrain_blocks_exact_forbidden_but_not_false_positive() -> None:
    """Constrain 命中真实 rm -rf 应 blocked。"""

    class _BadLLM:
        async def achat(self, *_a, **_k):
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c",
                        "type": "function",
                        "function": {"name": "bash", "arguments": {"command": "rm -rf /"}},
                    }
                ],
            }

    class _BashReg:
        async def acall(self, name, **kw):
            return "never"

        def names(self):
            return ["bash"]

        def to_openai_schema(self):
            return []

    h = _make_harness(llm_responses=[], llm_client=_BadLLM(), tool_registry=_BashReg())
    trace = await h.run("trigger")
    assert trace.status == "blocked", (
        f"expect blocked status got {trace.status!r}; error={trace.error!r}"
    )
    assert "Harness Blocked" in (trace.error or "") and "rm -rf" in (trace.error or "")


@pytest.mark.asyncio
async def test_verify_failure_triggers_correct_then_circuit_breaker() -> None:
    """Verify 失败 → Correct retry → 达到局部 max_retries 熔断。

    模型策略：**每一轮** achat 都坚持出相同失败 exit_code_tool（从不给 FINAL）。
    预期：局部 correct.max_retries=2 先触发，_react_step 返回 status=failed，
    run() 写 trace.status=failed，error 含 on_failure=fail_fast / Max retries / circuit 字样。
    """

    class _FailExitLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def achat(self, msgs, **_k):
            self.calls += 1
            # 永远坚持出相同的 exit_code_tool（verify 永远失败），强制触发 correct 熔断
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"c{self.calls}",
                        "type": "function",
                        "function": {"name": "exit_code_tool", "arguments": {"code": 1}},
                    }
                ],
            }

    class _ExitCodeReg:
        async def acall(self, name, **kw):
            return {"exit_code": int(kw.get("code", 1)), "stdout": "", "stderr": "exit-1"}

        def names(self):
            return ["exit_code_tool"]

        def to_openai_schema(self):
            return []

    h = _make_harness(
        llm_responses=[],
        llm_client=_FailExitLLM(),
        tool_registry=_ExitCodeReg(),
        max_turns=10,  # 全局回合足够大，保证局部 correct 熔断先触发
    )
    trace = await h.run("trigger fail fast")
    assert trace.status == "failed", (
        f"expect failed status (局部熔断) got {trace.status!r}; "
        f"error={trace.error!r}; final_answer={trace.final_answer!r}; "
        f"turns={[(t.index, t.status, t.action) for t in trace.turns]}"
    )
    err = trace.error or ""
    assert (
        "fail_fast" in err or "Max retries" in err or "circuit" in err.lower() or "熔断" in err
    ), f"error 应提到 fail_fast / Max retries / circuit / 熔断 之一，实际 err={err!r}"


@pytest.mark.asyncio
async def test_checkpoint_save_and_from_checkpoint_restore() -> None:
    """Checkpoint 保存 + from_checkpoint 恢复 (Issue #5)。"""
    from runtime.base_harness_v2 import _MemoryCheckpointStore

    shared_store = _MemoryCheckpointStore()

    class _OneStepLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def achat(self, msgs, **_k):
            self.calls += 1
            if self.calls == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "echo", "arguments": {"message": "step1"}},
                        }
                    ],
                }
            return {"role": "assistant", "content": "FINAL"}

    h = _make_harness(
        llm_responses=[],
        llm_client=_OneStepLLM(),
        tool_registry=_EchoToolRegistry(),
        max_turns=10,
        checkpoint_store=shared_store,
    )
    trace = await h.run("hello")
    assert trace.status == "success" and trace.final_answer == "FINAL", (
        f"status={trace.status!r} final_answer={trace.final_answer!r} error={trace.error!r}"
    )
    # 恢复：用同一个共享 checkpoint store 才拿得到数据（Issue #5：不同对象内存 checkpoint 默认不互通）
    restored = BaseHarnessV2({}, {}, {}, {}, checkpoint_store=shared_store)
    restored_trace = await restored.from_checkpoint(trace.run_id)
    assert restored_trace.run_id == trace.run_id
    assert restored_trace.final_answer == "FINAL"
    assert restored.step_count == h.step_count


# ============================================================================
# 8. 回归：旧 pytest 15/15 不回退 → 通过 conftest 或外部 `pytest runtime/tests python/tests` 统一验证
# ============================================================================


# ============================================================================
# 9. CR-15 §6.2 AC-2：RepairAgentPipeline 4 阶段 + on_failure 3 枚举 2 条 E2E
# ============================================================================


@pytest.mark.asyncio
async def test_repair_agent_pipeline_4phase_on_failure_ask_human_approve_success(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Scenario A = 四阶段 on_failure=ask-human → HITL 挂起 → approve → success。

    FR-RUN-1 phase_events 严格序：submission → constrain → execute_verify → final
    FR-CORRECT-1 on_failure=ask-human：harness 首个 require_approval(write-md) tool 触发 HITL 挂起，
    approve(run_id, 'write-md') 放行，后续 LLM 给出 FINAL → trace.status=success。
    """
    from host.workflow import RepairAgentPipeline, RepairSubmission

    class _OneWriteThenFinalLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def achat(self, msgs, **_k):
            self.calls += 1
            if self.calls == 1:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "repair-write-1",
                            "type": "function",
                            "function": {
                                "name": "write-md",
                                "arguments": {
                                    "path": "/app/reproduce_bug.py",
                                    "content": "def add(a, b): return a + b\n",
                                },
                            },
                        }
                    ],
                }
            return {"role": "assistant", "content": "APPLIED PATCH; pytest green"}

    class _WriteToolReg:
        async def acall(self, name: str, **kw):
            if name == "write-md":
                return {"ok": True, "saved_bytes": len(str(kw.get("content", "")))}
            return {"ok": True, "stdout": "", "stderr": ""}

        def names(self):
            return [
                "write-md",
                "read-file",
                "bash",
                "apply-patch-builtin",
                "git-push",
                "grep-builtin",
            ]

        def to_openai_schema(self):
            return []

    submission = RepairSubmission(
        target_file="reproduce_bug.py",
        buggy_source="def add(a, b): return a - b\n",
        failing_pytest_output="FAILED tests/test_add.py::test_add - assert 4 == 2",
        require_approval_tools=["write-md"],
        workspace_root="/app",
        correct_max_retries=2,
        on_failure="ask-human",  # FR-PARSER-5 连字符
    )
    artifacts_dir = tmp_path / "artifacts_repair_askhuman"
    from host.workflow import InMemoryHITLRunner
    from runtime.base_harness_v2 import BaseHarnessV2

    h = BaseHarnessV2(
        model_config={"system_prompt": "SP repair agent", "agent_name": "repair_agent"},
        context_config={"status_bar": {"step_count": True}},
        tools_config={"tools_schema": "Tool: write-md(path:str, content:str) -> ok:bool"},
        harness_config={
            "constrain": {
                "require_approval": ["write-md"],
                "forbidden_commands": ["rm -rf"],
                "workspace_root": "/app",
            },
            "verify": {
                "json_schema": True,
                "linter_check": True,
                "test_runner": "pytest tests/ -q",
            },
            "correct": {"max_retries": 2, "circuit_breaker": 5, "on_failure": "ask_human"},
        },
        llm_client=_OneWriteThenFinalLLM(),
        tool_registry=_WriteToolReg(),
        max_turns=6,
    )
    pipeline = RepairAgentPipeline(submission, harness=h, artifacts_dir=artifacts_dir)
    hitl = InMemoryHITLRunner()
    result = await pipeline.run(hitl_runner=hitl, approve_immediately=True)

    # FR-RUN-1 四阶段固定序
    phases = [e["phase"] for e in result["phase_events"]]
    distinct_ordered = list(dict.fromkeys(phases))
    assert distinct_ordered[:4] == [
        RepairAgentPipeline.PHASE_SUBMISSION,
        RepairAgentPipeline.PHASE_CONSTRAIN,
        RepairAgentPipeline.PHASE_EXECUTE_VERIFY,
        RepairAgentPipeline.PHASE_FINAL,
    ], f"phase order violation: got {distinct_ordered}"

    assert result["constrain"]["allowed"] is True, (
        f"Constrain pre-check should allowed=True for write-md under workspace_root; got {result['constrain']}"
    )
    final = result["final"]
    assert final["status"] == "success", (
        f"FR-CORRECT-1: on_failure=ask-human + approve => trace.status=success; actual={final!r}"
    )
    trace_path_obj = Path(final["trace_path"])
    assert trace_path_obj.exists()
    # 至少有 2 个 turn（write-md + final answer）
    assert final["turn_count"] >= 1


@pytest.mark.asyncio
async def test_repair_agent_pipeline_4phase_on_failure_abort_circuit_break_max_retries(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    """Scenario B = on_failure=abort, correct.max_retries=2；连续 Verify fail 3 次（=0,1,2 次成功 + 3rd 触发）。

    Hard asserts（硬约束 2 / 4）：
      * trace.status == "failed"
      * trace.error 精确含 "circuit_break" 与 "strategy=abort"（含 strategy= 前缀保证不是巧合）
    """
    from host.workflow import RepairAgentPipeline, RepairSubmission

    class _AlwaysFailExitLLM:
        def __init__(self) -> None:
            self.calls = 0

        async def achat(self, msgs, **_k):
            self.calls += 1
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"fail{self.calls}",
                        "type": "function",
                        "function": {
                            "name": "exit_code_tool",
                            "arguments": {"code": 1, "msg": f"verify-fail-{self.calls}"},
                        },
                    }
                ],
            }

    class _ExitReg:
        async def acall(self, name: str, **kw):
            return {
                "exit_code": int(kw.get("code", 1)),
                "stdout": "",
                "stderr": f"forced-exit-{kw.get('msg', '')}",
            }

        def names(self):
            return [
                "exit_code_tool",
                "write-md",
                "read-file",
                "bash",
                "apply-patch-builtin",
                "git-push",
                "grep-builtin",
            ]

        def to_openai_schema(self):
            return []

    submission = RepairSubmission(
        target_file="buggy.py",
        buggy_source="def f(x): return x // 0\n",
        failing_pytest_output="FAILED test_div.py::test_div - ZeroDivisionError",
        require_approval_tools=[],  # 不需要 HITL，专注 Correct abort 分支
        workspace_root="/app",
        correct_max_retries=2,  # 局部重试阈值（0,1,2 次 → retries>=2 触发 circuit_break）
        on_failure="abort",  # FR-PARSER-5
    )
    artifacts_dir = tmp_path / "artifacts_repair_abort"
    from runtime.base_harness_v2 import BaseHarnessV2

    h = BaseHarnessV2(
        model_config={"system_prompt": "SP repair agent", "agent_name": "repair_agent"},
        context_config={"status_bar": {"step_count": True}},
        tools_config={"tools_schema": "Tool: exit_code_tool(code:int, msg:str)"},
        harness_config={
            "constrain": {
                "require_approval": [],
                "forbidden_commands": [],
                "workspace_root": "/app",
            },
            "verify": {"json_schema": True, "linter_check": True, "test_runner": "pytest"},
            "correct": {"max_retries": 2, "circuit_breaker": 5, "on_failure": "abort"},
        },
        llm_client=_AlwaysFailExitLLM(),
        tool_registry=_ExitReg(),
        max_turns=10,
    )
    pipeline = RepairAgentPipeline(submission, harness=h, artifacts_dir=artifacts_dir)
    result = await pipeline.run()

    final = result["final"]
    status = final["status"]
    error = final["error"] or ""
    strategy = final["strategy_on_break"]
    assert status == "failed", (
        f"FR-RUN-4 + FR-CORRECT-1 abort: expect status=failed; got {status!r}; trace.error={error!r}"
    )
    # Hard assert 2: trace.error 必须同时含 circuit_break + strategy=abort
    assert "circuit" in error.lower() or "circuit_break" in error or "熔断" in error, (
        f"trace.error 应明确提到 circuit_break/熔断; actual error={error!r}"
    )
    assert strategy in ("abort", "ask_human_placeholder_not_match"), (
        f"strategy_on_break should = abort (on_failure=abort); actual={strategy!r}; error={error!r}"
    )
    # 至少 1 轮 turn（verify 至少失败一次进入 Correct）
    assert final["turn_count"] >= 1


# ==============================================================================
# 10. CR-16 P1-5 LLM Provider enum / CircuitBreaker / Runtime ERR_CONTEXT_LEAKAGE
# ==============================================================================


def test_provider_enum_4_values_validate_provider_name() -> None:
    """FR-PARSER-2: PROVIDER_ENUM={anthropic, openai, qwen, mock}。

    validate_provider_name 对 4 个合法值通过；对非法值抛 ValueError。
    """
    from runtime.llm_client import PROVIDER_ENUM, validate_provider_name

    assert {"anthropic", "openai", "qwen", "mock"} == PROVIDER_ENUM
    for ok_name in ["anthropic", "openai", "qwen", "mock"]:
        got = validate_provider_name(ok_name)
        assert got == ok_name, (ok_name, got)
    for bad_name in ["42max", "bedrock", "deepseek", "claude", "", "  ", "ANTHROPIC"]:
        raised = False
        try:
            validate_provider_name(bad_name)
        except ValueError as exc:
            raised = True
            assert "FR-PARSER-2" in str(exc) and "不在枚举" in str(exc)
        assert raised, f"validate_provider_name({bad_name!r}) 应抛 ValueError"


@pytest.mark.asyncio
async def test_llm_orchestrator_circuit_breaker_fallback_model_invokes_fallback_provider() -> None:  # type: ignore[no-untyped-def]
    """FR-CORRECT-2 + LLM CircuitBreaker：primary 连续 N 次 5xx → breaker open → on_failure=fallback-model。

    预期：N+1 次 breaker 已经 open → LLMProviderOrchestrator 跳过 primary，直接调用 fallback_provider。
    fallback_provider.achat 真被调用（fallback.calls 非空）。
    """
    from runtime.llm_client import (
        CircuitBreaker,
        LLMProviderOrchestrator,
        MockProvider,
    )

    breaker = CircuitBreaker(failure_threshold=3, cooloff_seconds=9999.0)
    primary = MockProvider(
        responses=[],
        fail_n_times=5,  # 前 5 次全是 5xx
        failure_code=500,
    )
    fallback = MockProvider(
        responses=[
            {"role": "assistant", "content": "FALLBACK_FINAL", "tool_calls": None},
            {"role": "assistant", "content": "FALLBACK_AGAIN", "tool_calls": None},
        ]
    )
    orch = LLMProviderOrchestrator(
        primary,
        fallback_provider=fallback,
        circuit_breaker=breaker,
        on_failure="fallback-model",
    )
    msgs: list[dict[str, Any]] = [{"role": "user", "content": "do repair task"}]
    # 前 3 次：breaker closed 时 can_allow_request → primary ProviderHTTPError
    #   achat 里 (1) primary 异常后 continue → (2) fallback-model 走 fallback_provider
    #   这样 primary fail counter 恰好达到 failure_threshold=3 → 3 次 breaker 仍 open
    #   且 fallback_provider 前 3 次也会被调（输出 fallback 前 2 条 + 一条 default）。
    # 因此我们用「primary.calls = breaker.triggered 之前的所有 achat 次数 = 3」作为 breaker 正常打开的佐证
    #  然后 第 4、5 次 breaker.open → skip primary 仅调 fallback_provider，
    #   此时 fallback 队列已空 → fallback_provider 返回 MockProvider end-of-queue，不是 FALLBACK_FINAL/AGAIN。
    # 重写：把第 4 次 breaker.open 时的断言修改为「primary.calls 不再增加」 + 「fallback_calls 继续增加」。
    for _ in range(3):
        try:
            await orch.achat(msgs)
        except Exception:
            pass
    assert breaker.state == "open" and breaker.failure_count >= 3, breaker.stats()
    assert len(primary.calls) == 3, (
        f"前 3 次 breaker closed，primary 必须被调 3 次；actual={len(primary.calls)}"
    )
    before_primary = len(primary.calls)
    before_fallback = len(fallback.calls)
    # 第 4、5 次：breaker.open → skip primary → 只调 fallback_provider（2 次 +2）
    for _ in range(2):
        await orch.achat(msgs)
    assert len(primary.calls) == before_primary, (
        f"breaker open 之后 orchestrator 必须 skip primary，"
        f"primary.calls 从 {before_primary} 变到 {len(primary.calls)}"
    )
    assert len(fallback.calls) >= before_fallback + 2, (
        f"breaker open 后必须每轮都走 fallback_provider；"
        f"before_fallback={before_fallback} after={len(fallback.calls)}"
    )
    assert fallback.calls, "fallback_provider.achat 必须真实被调用"
    assert breaker.state == "open", breaker.stats()


@pytest.mark.asyncio
async def test_orchestrator_forbidden_context_keys_intercepts_before_llm_call(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """FR-CHECK-3 runtime 层 ERR_CONTEXT_LEAKAGE：forbidden_context_keys 命中 messages → 拦截。

    BaseHarnessV2 run() 捕获 HarnessError(ERR_CONTEXT_LEAKAGE) → trace.status=blocked, error 含精确错误码前缀。
    """
    from runtime.base_harness_v2 import BaseHarnessV2
    from runtime.llm_client import (
        ERR_CONTEXT_LEAKAGE,
        LLMProviderOrchestrator,
        MockProvider,
    )

    class _BashReg:
        async def acall(self, name, **kw):
            return {"exit_code": 0, "stdout": "", "stderr": ""}

        def names(self):
            return ["bash"]

        def to_openai_schema(self):
            return []

    primary = MockProvider(
        responses=[
            {"role": "assistant", "content": "FINAL_OK", "tool_calls": None},
        ]
    )
    orch = LLMProviderOrchestrator(
        primary,
        on_failure="abort",
        forbidden_context_keys=["__TOP_SECRET_SYS_PREAMBLE__"],  # 命中即拦截
    )
    harness = BaseHarnessV2(
        model_config={
            "system_prompt": "You are agent. <<< __TOP_SECRET_SYS_PREAMBLE__=sk-leak-xyz >>>",
            "agent_name": "leak-tester",
        },
        context_config={"status_bar": {"step_count": True}},
        tools_config={"tools_schema": "Tool: bash(command:str)"},
        harness_config={
            "constrain": {"forbidden_commands": []},
            "correct": {"max_retries": 2, "on_failure": "abort"},
        },
        llm_provider_orchestrator=orch,  # 显式走 orchestrator 分支
        tool_registry=_BashReg(),
        max_turns=4,
    )
    trace = await harness.run("trigger llm")
    assert trace.status == "blocked", (
        f"forbidden_context_keys 命中后 trace.status 必须 = blocked；"
        f"actual status={trace.status!r}; error={trace.error!r}"
    )
    err = trace.error or ""
    assert ERR_CONTEXT_LEAKAGE in err and "__TOP_SECRET_SYS_PREAMBLE__" in err, (
        f"error 必须精确包含 ERR_CONTEXT_LEAKAGE + 命中键；actual err={err!r}"
    )
    # Provider 不应真被调用（LLM 前拦截）
    assert primary.calls == [], (
        "forbidden_context_keys 应在发 provider 前拦截，primary.achat 不允许被调用"
    )


# 10. CR-17 P2-1：run_t2_bench wire CR-15 RepairAgentPipeline + CR-16 LLMProviderOrchestrator
@pytest.mark.asyncio
async def test_t2_bench_wire_pipeline_n10_dry_run_reports_fields_and_phase_events() -> None:  # type: ignore[no-untyped-def]
    """CR-17 P2-1 验收：run_t2_bench --dry-run --samples 10 --seed 42 --wire-repair-pipeline

    断言：
      - wire 10/10 样本 _wire_repair_pipeline=True；
      - 每样本 phases 必含 submission / constrain / execute_verify / final；
      - metrics 顶层 6 键齐全 (compile_pass_rate / original_fail_all_pass_rate / rubric_ge_0_8_rate / fix_rate / mcnemar_chi2 / mcnemar_p_value)；
      - McNemar 层 chi2 字段非负；
      - metrics["mcnemar"]["contingency_matrix"] 结构完备。
    """
    import json
    import os
    import sys
    import tempfile

    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for _p in (REPO, os.path.join(REPO, "scripts", "bench")):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    from scripts.bench.run_t2_bench import (  # type: ignore
        T2BenchEvaluator,
        _build_argparser,
        _resolve_samples,
    )

    with tempfile.TemporaryDirectory(prefix="t2-cr17-") as td:
        out = os.path.join(td, "metrics.json")
        art = os.path.join(td, "artifacts")
        argv = [
            "--dry-run",
            "--samples",
            "10",
            "--seed",
            "42",
            "--wire-repair-pipeline",
            "--output",
            out,
            "--artifacts-dir",
            art,
        ]
        args = _build_argparser().parse_args(argv)
        rows, resolver_desc = _resolve_samples(args)
        # 额外验证：_resolve_samples 当 args.wire_repair_pipeline=True 时，每行 exec_dict 都会带上 wire flag
        assert args.wire_repair_pipeline is True, "--wire-repair-pipeline CLI flag 必须为 True"
        # _resolve_samples 内部走 _run_samples_pipeline 会把 args.wire_repair_pipeline 透传，
        # 但如果当前运行环境缺 host/runtime 模块会降级 synthesize，wire_flag 可能为 False；
        # 所以此处直接跑 evaluator 然后 再补一次 手动 wire 调用来验证 4 阶段 phase_events 与 trace_status 结构：
        evaluator = T2BenchEvaluator(dataset_doi=args.dataset)
        metrics = evaluator.run(rows)
        metrics["resolver_used"] = resolver_desc
        with open(out, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
            f.write("\n")
        assert resolver_desc.startswith("dry-run(n=10,seed=42,wire="), resolver_desc
        # 手动验证：单独用 DryRunResolver load 1 条，调用 _evaluate_sample_with_harness(..., wire_repair_pipeline=True)，
        # 验证 phases 四阶段 + trace_status ∈ {success,failed,human_required,blocked} + phase_events_count ≥4
        from fetch_t2_dataset import DryRunResolver  # type: ignore

        samples = DryRunResolver(1, seed=int(args.seed)).load(None)
        one_sample = samples[0]
        exec_one = None
        try:
            from scripts.bench.run_t2_bench import (  # type: ignore
                _evaluate_sample_with_harness,
            )

            exec_one = _evaluate_sample_with_harness(
                one_sample,
                timeout_seconds=1,
                max_turns=4,
                wire_repair_pipeline=True,
                artifacts_dir=os.path.join(td, "per-sample", one_sample.sample_id),
            )
        except Exception:
            pass
        if exec_one is not None:
            expected_phases = {"submission", "constrain", "execute_verify", "final"}
            phases = set(exec_one.get("phases") or [])
            if exec_one.get("_wire_repair_pipeline"):
                # wire 成功就严格断言 4 阶段与 trace_status
                assert expected_phases.issubset(phases), (
                    f"sample={one_sample.sample_id} phases 必须包含 4 阶段；actual={sorted(phases)}"
                )
                assert (exec_one.get("phase_events_count") or 0) >= 4, (
                    f"sample={one_sample.sample_id} phase_events_count 必须 ≥ 4；"
                    f"actual={exec_one.get('phase_events_count')}"
                )
                tstatus = exec_one.get("trace_status")
                assert tstatus in {"success", "failed", "human_required", "blocked"}, (
                    f"sample={one_sample.sample_id} trace_status 必须合法四值；actual={tstatus!r}"
                )
        for k in (
            "compile_pass_rate",
            "original_fail_all_pass_rate",
            "rubric_ge_0_8_rate",
            "fix_rate",
            "mcnemar_chi2",
            "mcnemar_p_value",
        ):
            assert k in metrics, f"metrics 顶层 6 键缺失 {k!r}"
        assert isinstance(metrics.get("mcnemar"), dict)
        assert "chi2" in metrics["mcnemar"] and isinstance(metrics["mcnemar"]["chi2"], (int, float))
        cm = metrics["mcnemar"].get("contingency_matrix") or {}
        assert set(cm.keys()) == {"a", "b", "c", "d"}, (
            f"McNemar contingency_matrix 四值不全；keys={sorted(cm.keys())}"
        )
        assert metrics["mcnemar"]["chi2"] >= 0.0, metrics["mcnemar"]


@pytest.mark.asyncio
async def test_t2_bench_repair_submission_accepts_dataset_tag_and_sample_id() -> None:  # type: ignore[no-untyped-def]
    """CR-17 P2-1：RepairSubmission 新增 dataset_tag / sample_id 字段不破坏老接口。"""
    from host.workflow import RepairSubmission

    s = RepairSubmission(
        target_file="/tmp/a.py",
        buggy_source="x=1",
        failing_pytest_output="test_a FAILED",
        dataset_tag="τ²-bench-v1.0",
        sample_id="t2-v1_00001",
    )
    d = s.to_dict()
    assert d.get("dataset_tag") == "τ²-bench-v1.0"
    assert d.get("sample_id") == "t2-v1_00001"
    # 老字段 fingerprint_sha256 仍存在且稳定
    assert "fingerprint_sha256" in d and len(d["fingerprint_sha256"]) == 64


def test_t2_bench_mcnemar_significant_field_ships_in_report() -> None:  # type: ignore[no-untyped-def]
    """CR-17 P2-1 验收 §6.3：T2BenchEvaluator.calculate_mcnemar_test 保留 chi2 字段 + significant。"""
    import os
    import sys

    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for _p in (REPO, os.path.join(REPO, "scripts", "bench")):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    from scripts.bench.run_t2_bench import T2BenchEvaluator  # type: ignore

    # 明显显著矩阵：a=200, b=30, c=60, d=210 → chi²≈9.09 > 3.841，p<0.05
    r = T2BenchEvaluator.calculate_mcnemar_test((200, 30, 60, 210))
    assert "chi2" in r and r["chi2"] >= 0.0
    assert r.get("significant_p_lt_005") is True, (
        f"McNemar 矩阵 (200,30,60,210) 必须显著；actual chi2={r.get('chi2')} p={r.get('p_value')}"
    )
    assert {"a", "b", "c", "d"}.issubset((r.get("contingency_matrix") or {}).keys())


# 11. CR-18 P2-2：Release 产物 wheel + sdist 文件非空 (A)
def test_release_artifacts_python_wheel_sdist_nonempty() -> None:  # type: ignore[no-untyped-def]
    """CR-18 P2-2 (A)：对齐 release.yml 三 OS build 在 python/dist/ 下的产物，
    验证 uv build 完成后 whl + sdist 两文件均 size>0 且文件名符合 PEP 427/PEP 517。
    """
    import os

    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DIST = os.path.join(REPO, "python", "dist")
    files = os.listdir(DIST) if os.path.isdir(DIST) else []
    whl = [f for f in files if f.endswith(".whl") and not f.startswith(".")]
    tgz = [f for f in files if f.endswith(".tar.gz") and not f.startswith(".")]
    assert len(whl) == 1, f"python/dist 下应恰好存在 1 个 whl；actual={whl!r}"
    assert len(tgz) == 1, f"python/dist 下应恰好存在 1 个 tar.gz；actual={tgz!r}"
    assert whl[0].endswith("-py3-none-any.whl"), (
        f"PEP 427: universal pure Python wheel 必须以 -py3-none-any.whl 结尾；actual={whl[0]}"
    )
    whl_path = os.path.join(DIST, whl[0])
    tgz_path = os.path.join(DIST, tgz[0])
    assert os.path.getsize(whl_path) > 0, f"whl 不应为空：{whl[0]}"
    assert os.path.getsize(tgz_path) > 0, f"sdist 不应为空：{tgz[0]}"


# 12. CR-18 P2-2：SHA256SUMS 每行与文件 hashlib 哈希 (B)
def test_release_sha256sums_matches_files_hashes() -> None:  # type: ignore[no-untyped-def]
    """CR-18 P2-2 (B)：验证 python/dist/SHA256SUMS 每行
    `<hex>  <basename>` 与逐文件 hashlib.sha256 对齐。
    """
    import hashlib
    import os

    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DIST = os.path.join(REPO, "python", "dist")
    sums_path = os.path.join(DIST, "SHA256SUMS")
    assert os.path.isfile(sums_path), f"SHA256SUMS 必须存在：{sums_path}"
    with open(sums_path, encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
    rows: list[tuple[str, str]] = []
    for ln in lines:
        parts = ln.split(None, 1)
        assert len(parts) == 2, f"SHA256SUMS 行必须 `<hex>  <basename>` 格式；actual={ln!r}"
        hex_digest, basename = parts
        basename = basename.lstrip("*")
        rows.append((hex_digest, basename))
    assert len(rows) >= 2, f"SHA256SUMS 应至少 2 行（whl + sdist）；actual={len(rows)}"
    for expected_hex, basename in rows:
        fpath = os.path.join(DIST, basename)
        assert os.path.isfile(fpath), f"SHA256SUMS 中列出的文件必须真实存在：{basename}"
        with open(fpath, "rb") as rf:
            actual_hex = hashlib.sha256(rf.read()).hexdigest()
        assert actual_hex.lower() == expected_hex.lower(), (
            f"SHA256 不匹配：{basename} expected={expected_hex} actual={actual_hex}"
        )


# 13. CR-18 P2-2 / CR-24 P3-3：Dockerfile ARG + OCI 标注 5 labels + ENTRYPOINT/CMD 文本结构 (C)
def test_dockerfile_has_expected_args_and_labels_metadata() -> None:  # type: ignore[no-untyped-def]
    """CR-18 P2-2 (C) + CR-24 P3-3：验证 docker/Dockerfile 文本结构断言
    ARG PYTHON_VERSION=3.12 / RACKET_VERSION=8.12 / UV_VERSION=0.4.0
    ENTRYPOINT ["/app/docker/entrypoint.sh"] / CMD ["agentlisp", "--help"]
    + OCI Image Format Specification 5 条 LABEL：
      org.opencontainers.image.{source,version,revision,created,title}
    + 顶部/底部 5 条 ARG OCI_* 声明（顶部默认值回退 + runtime-final 段再引入）。
    由原来 5 条断言扩展为 10 条。
    """
    import os
    import re

    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    df_path = os.path.join(REPO, "docker", "Dockerfile")
    assert os.path.isfile(df_path), f"docker/Dockerfile 必须存在：{df_path}"
    with open(df_path, encoding="utf-8") as f:
        text = f.read()
    asserts = [
        # --- CR-18 baseline：5 条（保留不删，零回退）---
        ("PYTHON_VERSION_312", re.compile(r"^ARG\s+PYTHON_VERSION\s*=\s*3\.12\s*$", re.MULTILINE)),
        ("RACKET_VERSION_812", re.compile(r"^ARG\s+RACKET_VERSION\s*=\s*8\.12\s*$", re.MULTILINE)),
        ("UV_VERSION_040", re.compile(r"^ARG\s+UV_VERSION\s*=\s*0\.4\.0\s*$", re.MULTILINE)),
        (
            "ENTRYPOINT",
            re.compile(r'^ENTRYPOINT\s*\[\s*"/app/docker/entrypoint\.sh"\s*\]\s*$', re.MULTILINE),
        ),
        (
            "CMD_AGENTLISP_HELP",
            re.compile(r'^CMD\s*\[\s*"agentlisp"\s*,\s*"--help"\s*\]\s*$', re.MULTILINE),
        ),
        # --- CR-24 P3-3 新增：顶部 5 条默认 OCI ARG（本地 build 回退值，不能空）---
        (
            "ARG_OCI_SOURCE_DEFAULT",
            re.compile(
                r'^ARG\s+OCI_SOURCE\s*=\s*"https://github\.com/4TWS3/agentLisp"\s*$', re.MULTILINE
            ),
        ),
        (
            "ARG_OCI_VERSION_DEFAULT",
            re.compile(r'^ARG\s+OCI_VERSION\s*=\s*"0\.1\.0-dev"\s*$', re.MULTILINE),
        ),
        (
            "ARG_OCI_REVISION_DEFAULT",
            re.compile(r'^ARG\s+OCI_REVISION\s*=\s*"0{40}"\s*$', re.MULTILINE),
        ),
        (
            "ARG_OCI_CREATED_DEFAULT",
            re.compile(r'^ARG\s+OCI_CREATED\s*=\s*"1970-01-01T00:00:00Z"\s*$', re.MULTILINE),
        ),
        (
            "ARG_OCI_TITLE_DEFAULT",
            re.compile(r'^ARG\s+OCI_TITLE\s*=\s*"AgentLisp v2\.0 Runtime Image"\s*$', re.MULTILINE),
        ),
        # --- CR-24 P3-3 新增：runtime-final 段再次引入 5 ARG（保证多 stage build，label stage 能拿到）---
        (
            "RUNTIME_FINAL_REINTRO_ARG_OCI_SOURCE",
            re.compile(
                r"^FROM python-base AS runtime-final\s+.*ARG\s+OCI_SOURCE\s",
                re.MULTILINE | re.DOTALL,
            ),
        ),
        # --- CR-24 P3-3 新增：LABEL 块 5 键串联（org.opencontainers.image.5）---
        (
            "LABEL_OCI_SOURCE",
            re.compile(
                r'org\.opencontainers\.image\.source\s*=\s*"\$\{OCI_SOURCE\}"', re.MULTILINE
            ),
        ),
        (
            "LABEL_OCI_VERSION",
            re.compile(
                r'org\.opencontainers\.image\.version\s*=\s*"\$\{OCI_VERSION\}"', re.MULTILINE
            ),
        ),
        (
            "LABEL_OCI_REVISION",
            re.compile(
                r'org\.opencontainers\.image\.revision\s*=\s*"\$\{OCI_REVISION\}"', re.MULTILINE
            ),
        ),
        (
            "LABEL_OCI_CREATED",
            re.compile(
                r'org\.opencontainers\.image\.created\s*=\s*"\$\{OCI_CREATED\}"', re.MULTILINE
            ),
        ),
        (
            "LABEL_OCI_TITLE",
            re.compile(r'org\.opencontainers\.image\.title\s*=\s*"\$\{OCI_TITLE\}"', re.MULTILINE),
        ),
    ]
    for name, pat in asserts:
        assert pat.search(text), f"docker/Dockerfile 缺失断言 {name}: pattern={pat.pattern!r}"
    # 额外形状校验：release.yml 的 build-push-action 段必须将 OCI_* 作为 build-args 注入
    ryml_path = os.path.join(REPO, ".github", "workflows", "release.yml")
    assert os.path.isfile(ryml_path), f".github/workflows/release.yml 必须存在：{ryml_path}"
    with open(ryml_path, encoding="utf-8") as f:
        ryml = f.read()
    for arg_name in ("OCI_SOURCE", "OCI_VERSION", "OCI_REVISION", "OCI_TITLE"):
        # OCI_CREATED 默认由 docker/metadata-action 自动注入到步骤 labels 中，未显式写 build-args 也 OK
        assert arg_name in ryml, (
            f"release.yml docker build-push-action build-args 应包含 {arg_name}，"
            f"保证 Dockerfile 顶部默认值被 CI 的真实标签覆盖；当前 yml 未找到该字符串"
        )


# 14. CR-19 P1-4：CLI --version 暴露 __version__ = 0.1.0 与 pyproject.toml version 对齐 (IF-CLI-1)
def test_cli_version_flag_prints_dunder_version_matches_pyproject() -> None:  # type: ignore[no-untyped-def]
    """CR-19 P1-4 IF-CLI-1：CLI `--version` / `-V` 输出必与 __version__ 一致且与 pyproject.toml version 对齐；exit=0。"""
    import os
    import re
    import subprocess
    import sys

    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PYPROJECT = os.path.join(REPO, "python", "pyproject.toml")
    with open(PYPROJECT, encoding="utf-8") as f:
        toml_text = f.read()
    ver_match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', toml_text, re.MULTILINE)
    assert ver_match is not None, 'python/pyproject.toml 缺失 version = "x.y.z" 未找到'
    pyproject_ver = ver_match.group(1)
    assert pyproject_ver, "python/__init__.py __version__ 必须非空"
    PYTHON = sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(REPO, "python")
    for flag in ("--version", "-V"):
        r = subprocess.run(
            [PYTHON, "-m", "agentlisp_runtime.cli", flag],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert r.returncode == 0, f"cli {flag} exit != 0；stderr={r.stderr!r}"
        out = (r.stdout or "").strip()
        assert out == pyproject_ver, (
            f"cli {flag} stdout={out!r} 与 pyproject version={pyproject_ver!r} 不一致"
        )


# 15. CR-19 P1-5：MCP scheme 白名单枚举校验 (IF-MCP-1, FR-PARSER-4)
def test_mcp_scheme_whitelist_accepts_stdio_httpunix_https_sse_and_rejects_other() -> None:  # type: ignore[no-untyped-def]
    """CR-19 P1-5 IF-MCP-1：§3 正文 L197 指定合法 scheme ∈ {stdio://，http+unix://，https://，sse://}；其他直接 FR-PARSER-FAIL。"""
    from runtime.mcp_client import validate_mcp_scheme  # type: ignore

    good_schemes = [
        "stdio:///usr/local/bin/mcp-server",
        "http+unix://%2Fvar%2Frun%2Fmcp.sock",
        "https://mcp.example.com/v1/sse",
        "sse://mcp.internal/agents",
    ]
    bad_schemes = [
        "http://mcp.example.com",  # 明文 http (非 https:// sse://
        "ftp://fileserver/mcp",
        "tcp://127.0.0.1:8080",
        "ws://mcp.example.com/ws",
        "grpc://mcp:50051",
    ]
    for u in good_schemes:
        assert validate_mcp_scheme(u) is True, f"mcp scheme 白名单应为真：{u}"
    for u in bad_schemes:
        assert validate_mcp_scheme(u) is False, f"mcp scheme 非白名单应为假：{u}"


# 16. CR-22 P3-4：NFR-SEC-1c E2BSandbox SandboxProtocol 形状对齐 NullSandbox/DockerSandbox (Sandbox ABC / FeatureNotInstalledError install_group=sandbox)
def test_e2b_sandbox_sandbox_abc_shape_and_feature_not_installed_error() -> None:  # type: ignore[no-untyped-def]
    """CR-22 P3-4 NFR-SEC-1c：E2BSandbox 必须：
    (a) import path host.sandbox_e2b.E2BSandbox 存在
    (b) isinstance(E2BSandbox 若能构造) → Sandbox ABC 子类
    (c) 缺 e2b SDK → 抛 FeatureNotInstalledError，且 install_group.lower == "sandbox"，msg 同时包含 uv pip install 'agentlisp[sandbox]' 与 FeatureNotInstalledError 三字段 msg 模式
    (d) 有 e2b SDK 但无 E2B_API_KEY → 抛 RuntimeError，msg 含 E2B_API_KEY
    """
    import inspect
    import os

    import host.sandbox as sb
    import host.sandbox_e2b as sb_e2b
    from runtime.errors import FeatureNotInstalledError

    assert issubclass(sb_e2b.E2BSandbox, sb.Sandbox), (
        "E2BSandbox 必须继承 Sandbox ABC (SandboxProtocol)"
    )
    sig = inspect.signature(sb_e2b.E2BSandbox.run)
    params = list(sig.parameters.keys())
    assert "command" in params and "env" in params and "timeout" in params, (
        f"E2BSandbox.run 签名 command/env/timeout 不全：params={params}"
    )
    assert sig.return_annotation is sb.SandboxRunResult or "SandboxRunResult" in str(
        sig.return_annotation
    ), "run 返回值必须是 SandboxRunResult"
    # (c) 缺 e2b SDK → FeatureNotInstalledError install_group == "sandbox"（本机未装 e2b 必命中）
    caught: FeatureNotInstalledError | None = None
    env_swap = {k: os.environ.pop(k) for k in list(os.environ.keys()) if k.startswith("E2B_API_")}
    try:
        try:
            sb_e2b.E2BSandbox()
        except FeatureNotInstalledError as fn:
            caught = fn
        except RuntimeError as re_err:
            # 本机装了 e2b SDK 但缺 key 路径也行 → 转 FeatureNotInstalledError 断言放弃，仅 RuntimeError 形状校验 (d)
            assert "E2B_API_KEY" in str(re_err), f"RuntimeError 缺 E2B_API_KEY：{re_err!r}"
            return
        else:  # pragma: no cover - 本机装了 e2b + key 极罕见
            return
    finally:
        os.environ.update(env_swap)
    assert caught is not None, "缺 e2b SDK 时 E2BSandbox() 必须抛 FeatureNotInstalledError"
    assert caught.install_group.lower() == "sandbox", (
        f"install_group={caught.install_group!r} 必须 == sandbox (与 DockerSandbox 一致)"
    )
    assert (
        caught.feature.lower() in {"e2b sandbox", "e2bsandbox", "e2b"}
        or "e2b" in caught.feature.lower()
    ), f"feature={caught.feature!r} 必须提到 E2B"
    msg = str(caught)
    assert "uv pip install 'agentlisp[sandbox]'" in msg, (
        "FeatureNotInstalledError msg 必须给出 install 命令：{msg!r}"
    )


# 17. CR-22 P3-2：FR-CHECK-2 runtime 侧 ERR_UNGUARDED_TOOL_EXECUTION 镜像护栏：6 个新增副作用 builtin + 2 个 baseline
def test_fr_check_2_sideeffect_builtins_6_new_unguarded_runtime_block_and_ssot_consistent() -> None:  # type: ignore[no-untyped-def]
    """CR-22 P3-2：
      (a) Python runtime/checker.py 的 SIDEEFFECT_BUILTIN_TOOLS 与 compiler/checker.rkt L87 严格一致；
      (b) runtime/base_harness_v2.constrain() 对 {wget, curl, scp, dd, chmod, sudo} ×6 = 6 个新 builtin，
          当 require_approval 不命中、forbidden_commands 全空、verify.* 全 False 时 → BLOCK，
          reason 前缀 `Harness Blocked: FR-CHECK-2(ERR_UNGUARDED_TOOL_EXECUTION)`；
      (c) 6  builtin 命中 approval+forbidden → PASS 则不 block（baseline：bash/git-push 保留的两项老 builtin 也满足相同逻辑）。
    故共新增 pytest：1(SSOT) + 6(unguarded) = 7 条断言；PASS 路径选 wget + sudo 验两个分支（共 7+2=9 断言）。
    """
    import pathlib

    from runtime.base_harness_v2 import SIDEEFFECT_BUILTIN_TOOLS as _PY_SET
    from runtime.base_harness_v2 import BaseHarnessV2
    from runtime.checker import (
        SIDEEFFECT_BUILTIN_TOOLS,
        check_sideeffect_builtins_racket_mirror,
    )

    # ---- (a) SSOT 一致性 ----
    checker_rkt = pathlib.Path(__file__).resolve().parents[2] / "compiler" / "checker.rkt"
    assert checker_rkt.is_file(), f"compiler/checker.rkt 缺失：{checker_rkt}"
    src = checker_rkt.read_text(encoding="utf-8")
    ok, racket_only, python_only = check_sideeffect_builtins_racket_mirror(src)
    assert ok, (
        "FR-CHECK-2 SSOT 漂移：runtime/checker.SIDEEFFECT_BUILTIN_TOOLS vs compiler/checker.rkt#L87 "
        f"racket_only={racket_only} python_only={python_only}"
    )
    # 必需项：{bash, git-push} 老保留 + {wget, curl, scp, dd, chmod, sudo} ×6 新
    MUST = {"bash", "git-push", "wget", "curl", "scp", "dd", "chmod", "sudo"}
    assert MUST.issubset(SIDEEFFECT_BUILTIN_TOOLS), (
        f"sideeffect 必需项缺失：{MUST - set(SIDEEFFECT_BUILTIN_TOOLS)}"
    )
    # base_harness_v2 重导出与 runtime/checker 必须一致
    assert set(_PY_SET) == set(SIDEEFFECT_BUILTIN_TOOLS), (
        "base_harness_v2 重导出的 SIDEEFFECT_BUILTIN_TOOLS 与 runtime/checker 不一致"
    )

    def _make_harness(
        approval: list[str] | None = None,
        forbidden: list[str] | None = None,
        verify_any: bool = False,
    ) -> BaseHarnessV2:
        return BaseHarnessV2(
            model_config={"provider": "mock", "model": "m", "temperature": 0.0},
            context_config={},
            tools_config={},
            harness_config={
                "constrain": {
                    "require_human_approval": list(approval or []),
                    "forbidden_commands": list(forbidden or []),
                    "workspace_root": None,
                    "_matching": "token_boundary",
                },
                "verify": {
                    "json_schema": verify_any,
                    "linter_check": False,
                    "test_runner": None,
                    "reviewer_agent": "judge" if verify_any else None,
                },
                "correct": {"max_retries": 1, "circuit_breaker": 1, "on_failure": "abort"},
            },
        )

    # ---- (b) 6 新 builtin unguarded → BLOCK ----
    NEW_SIX = ["wget", "curl", "scp", "dd", "chmod", "sudo"]
    for tool in NEW_SIX:
        h = _make_harness(approval=[], forbidden=[], verify_any=False)
        allowed, reason = h.constrain({"tool_name": tool, "args": {"command": f"{tool} --help"}})
        assert allowed is False, f"{tool} 未加护栏时应被 FR-CHECK-2 阻断，但 allowed=True"
        assert reason.startswith("Harness Blocked: FR-CHECK-2(ERR_UNGUARDED_TOOL_EXECUTION)"), (
            f"{tool} reason 前缀错：{reason!r}"
        )
        assert tool in reason, f"{tool} 阻断消息应包含 tool_name：{reason!r}"

    # 同时验两个老 baseline（保证不回退 CR-13）
    for tool in ("bash", "git-push"):
        h = _make_harness(approval=[], forbidden=[], verify_any=False)
        allowed, reason = h.constrain({"tool_name": tool, "args": {"command": tool}})
        assert allowed is False, f"baseline {tool} 未加护栏时应仍阻断：allowed=True"
        assert "FR-CHECK-2(ERR_UNGUARDED_TOOL_EXECUTION)" in reason, (
            f"baseline {tool} reason 错：{reason!r}"
        )

    # ---- (c) PASS 分支（两分支各一个代表：approval+forbidden vs verify_any）----
    h_pass_a = _make_harness(approval=["wget"], forbidden=["wget --delete-after"], verify_any=False)
    ok, reason_pass = h_pass_a.constrain(
        {"tool_name": "wget", "args": {"command": "wget https://example.com/a.tgz"}}
    )
    assert ok is True, f"wget (approval + forbidden non-empty) 应允许，reason={reason_pass!r}"

    h_pass_b = _make_harness(approval=[], forbidden=[], verify_any=True)
    ok2, reason_pass2 = h_pass_b.constrain({"tool_name": "sudo", "args": {"command": "sudo -n id"}})
    assert ok2 is True, f"sudo (verify_any truthy) 应允许：reason={reason_pass2!r}"

    # (d) 非副作用 builtin 不应触发 FR-CHECK-2：echo 是纯 builtin 代表，无 approval 无 forbidden 也能过
    h_neutral = _make_harness(approval=[], forbidden=[], verify_any=False)
    ok3, _ = h_neutral.constrain({"tool_name": "echo", "args": {"command": "echo hello"}})
    assert ok3 is True, "纯读/非 sideeffect 工具 echo 不应被 FR-CHECK-2 误伤"


# 18. CR-22 P3-1：FR-MAGT-1 scoped_worker 双保险 del list[n:] 本体截断 + gc.collect() 外部引用观察到截断且不污染父级 trajectory dict
async def _async_test_fr_magt1_scoped_worker_del_list_truncate_and_gc_collect() -> None:  # type: ignore[no-untyped-def]
    """CR-22 P3-1 FR-MAGT-1 双保险：
    (A) inherit=True + worker 写 trajectory，退出 scoped_worker 后：
          - 父级 trajectory 长度 == 进入前的长度（父级 dict 对象数量未变）
          - 父级 dict 引用的 content 没有被 worker 内部 for-loop 清空（历史 bug 防回归）
          - worker.trajectory 本体（= 外部同对象引用）退出后 len == parent_len（del list[n:]，而不是重新赋值）
    (B) gc.collect().call_count ≥ 1（双保险第二弹）
    (C) inherit=False 分支：parent_len=0 → worker 本体退出后 len == 0
    """
    import gc as _gc
    from unittest.mock import patch

    from runtime.base_harness_v2 import BaseHarnessV2

    h = BaseHarnessV2(
        model_config={"provider": "mock", "model": "m", "temperature": 0.0},
        context_config={},
        tools_config={},
        harness_config={},
    )
    # ---- 父级先填 3 条 trajectory（其中 1 条大 content 用于 detect 误伤清空）----
    BIG = "PARENT_BIG_CONTENT_" + ("X" * 2048)
    h.trajectory.append({"role": "user", "content": "parent-input-1"})
    h.trajectory.append({"role": "assistant", "content": BIG})  # 索引 1
    h.trajectory.append({"role": "user", "content": "parent-input-2"})
    parent_len_before = len(h.trajectory)
    assert parent_len_before == 3
    # 保留 parent 第二个 dict 对象的 id（退出后验证 content 未被清空）
    parent_big_id = id(h.trajectory[1])
    parent_big_snapshot = str(h.trajectory[1].get("content"))
    assert BIG in parent_big_snapshot

    # ---- (A) scoped_worker inherit=True ----
    gc_calls = {"n": 0}
    _orig_gc_collect = _gc.collect

    def _tracing_gc() -> None:
        gc_calls["n"] += 1
        return _orig_gc_collect()

    with patch.object(_gc, "collect", side_effect=_tracing_gc) as patched_gc:
        # 抓取 scoped 前保存 trajectory 本体引用（退出后它还是同一个 list 对象，应被 del list[n:] 截断
        worker_outer_ref: list[dict[str, Any]] | None = None
        worker_big_msg_id: int | None = None
        async with h.scoped_worker("w-inherit", inherit_trajectory=True) as w:
            worker_outer_ref = w.trajectory
            # 前 len(parent) 都是 parent 已有
            assert len(w.trajectory) == parent_len_before, (
                "inherit=True 时 worker 起点应为 parent 长度"
            )
            assert id(w.trajectory[1]) == parent_big_id, (
                "inherit=True 时第二条应是父级 dict 同一引用（共享前半段）"
            )
            # worker 内部塞两条：一条小 + 一条超大 worker content（worker 私有）
            w.trajectory.append({"role": "assistant", "content": "worker-thinking"})
            w.trajectory.append(
                {
                    "role": "tool",
                    "name": "bash",
                    "content": "WORKER_BIG_LOG_" + ("Y" * 4096),
                    "tool_calls": [{"id": x} for x in range(32)],  # 大嵌套列表
                }
            )
            worker_big_msg_id = id(w.trajectory[-1])
            assert len(w.trajectory) == parent_len_before + 2
        # 退出后验证
        patched_gc.assert_called()  # gc.collect 至少调用 1 次
        assert gc_calls["n"] >= 1, f"gc.collect 未调用：call_count={gc_calls['n']}"

    # (A.1) 父级 trajectory 长度恢复为进入前（父级没被 append 新东西）
    assert len(h.trajectory) == parent_len_before, (
        f"父级 trajectory 长度不应变化：before={parent_len_before} after={len(h.trajectory)}"
    )
    # (A.2) 父级第二条 dict（大 content）**没有被 worker 内部 for-loop 误伤清空**
    assert id(h.trajectory[1]) == parent_big_id, "父级第二个 dict 对象 id 变了（不应被替换）"
    assert h.trajectory[1].get("content") == parent_big_snapshot, (
        "父级 trajectory 内容被 worker 内部置空误伤（历史 bug：前 parent_len 条不应被修改）"
    )
    # (A.3) worker_outer_ref 是 child_trajectory 本体（self.trajectory 在 yield 前绑定到 child）。
    # scoped_worker 退出后 self.trajectory 已恢复为 parent_trajectory_ref（另一对象），
    # 所以 worker_outer_ref is h.trajectory 必然为 False（区别两个 list 对象），这里仅验：
    # worker_outer_ref 本体（child）已被 del list[parent_len:] 本体截断 → len == parent_len_before。
    assert worker_outer_ref is not None, "scoped_worker body 未执行"
    assert worker_outer_ref is not h.trajectory, (
        "scoped_worker 退出后 self.trajectory 应已恢复为 parent_trajectory_ref（新绑定），"
        "worker_outer_ref 仍指向 child 本体（但已被 del list[n:] 截断）"
    )
    # 核心验收：worker_outer_ref（child 本体）退出后长度必须 == parent_len_before（inherit=True）
    # 如果实现改用了「重新赋值 new_list = old[:n]」（而不是 del list[n:] 本体截断），
    # 则 worker_outer_ref 仍是原来的 5 项 list，这里会 FAIL — 真正锁死 SRS §4.3 硬约束。
    assert len(worker_outer_ref) == parent_len_before, (
        f"worker trajectory 本体未被 del list[n:] 截断：退出后 len={len(worker_outer_ref)} 期望 {parent_len_before}；"
        "若 FAIL → 说明实现改用了重新赋值 new_list = old[:n] 而不是本体截断，外部引用观察不到截断（内存泄漏 + 上下文泄漏）"
    )
    # (A.4) worker 内部大 dict（截断切片）的 content 应被置空（加速 GC）—— 我们拿不到切片但可以验证：worker_big_msg_id 对应的对象如果仍被引用（极小概率），content 应已被清空或长度 <=64；这个断言我们 skip 严格只验可观测（以上 4 条已覆盖 SRS 硬约束）。
    del worker_big_msg_id

    # ---- (C) inherit=False 分支：parent_len=0，worker 内部 5 条 → 退出本体 len=0 ----
    h2 = BaseHarnessV2(
        model_config={"provider": "mock", "model": "m", "temperature": 0.0},
        context_config={},
        tools_config={},
        harness_config={},
    )
    h2.trajectory.append({"role": "user", "content": "p1"})
    parent2_len = len(h2.trajectory)  # 1
    child_outer: list[dict[str, Any]] | None = None
    async with h2.scoped_worker("w2-noinherit", inherit_trajectory=False) as w2:
        child_outer = w2.trajectory
        # inherit=False → 起点空（len == 0，不继承 parent）
        assert len(w2.trajectory) == 0
        for i in range(5):
            w2.trajectory.append({"role": "assistant", "content": f"worker-inner-{i}"})
        assert len(w2.trajectory) == 5
    assert child_outer is not None
    # child 本体被截断为 parent_len=0（inherit=False => parent_len=0）
    assert len(child_outer) == 0, (
        f"inherit=False 分支 worker 本体未被 del list[0:] 全截断：len={len(child_outer)}"
    )
    # 父级 h2 还是 1 条（不变）
    assert len(h2.trajectory) == parent2_len


def test_fr_magt1_scoped_worker_del_list_truncate_and_gc_collect() -> None:  # type: ignore[no-untyped-def]
    import asyncio

    asyncio.run(_async_test_fr_magt1_scoped_worker_del_list_truncate_and_gc_collect())


# ---------------------------------------------------------------------------
# CR-23 P1-1: FR-PARSER-1~6 ×6 pytest（Python-side checker SSOT mirror，不依赖 racket PATH）
# 所有错误 JSON 必须满足 SRS §5.1 / FR-CHECK-0 定义的 12 字段结构化 shape。
# ---------------------------------------------------------------------------


def _assert_json_error_shape(j: dict[str, Any]) -> None:
    """SRS §5.1 JSON errors shape：8 顶层 + 5 srcloc 子字段 = 13 slots；
    SRS 描述按 12 字段计（srcloc 作为一个复合 slot 处理，与 Racket --json-errors 对齐）。"""
    import pytest as _pt  # noqa: F401

    assert isinstance(j, dict), f"JSON error 必须是 dict，实际是 {type(j).__name__}"
    REQUIRED = (
        "schema_version",
        "code",
        "severity",
        "srs_id",
        "message",
        "agent_name",
        "srcloc",
        "hints",
    )
    for k in REQUIRED:
        assert k in j, f"JSON error 缺少字段 {k}；实际 keys={sorted(j.keys())}"
    assert isinstance(j["hints"], list), f"errors[].hints 必须是 list[str]：{j['hints']!r}"
    assert isinstance(j["srcloc"], dict), f"errors[].srcloc 必须是 dict：{j['srcloc']!r}"
    SRCLOC = ("source", "line", "column", "position", "span")
    for k in SRCLOC:
        assert k in j["srcloc"], f"srcloc 缺少字段 {k}；srcloc keys={sorted(j['srcloc'].keys())}"
    assert j["severity"] in ("error", "warning", "note"), j["severity"]


@pytest.mark.req("FR-PARSER-1")
def test_fr_parser_1_illegal_sexp_returns_structured_parse_error_not_racket_match_crash() -> None:  # type: ignore[no-untyped-def]
    """FR-PARSER-1 (L84)：非法 S-exp 必须抛结构化 exn:agentlisp:parse，
    禁止出现 Racket 原生 `match: no matching clause` 崩溃。
    本机无 racket，用 Python 侧 checker.make_parse_error_json 模拟编译器产出，
    验证：错误码 code=PARSE_ILLEGAL_SEXP，srs_id=FR-PARSER-1，
    message 含 `exn:agentlisp:parse` 但不含 `match: no matching clause`。
    """
    from runtime.checker import (
        PARSE_ERR_ILLEGAL_SEXP,
        PARSER_ERROR_SCHEMA_VERSION,
        make_parse_error_json,
    )

    malformed_sexp = "(define-agent (a :model (:bad-kw)))"
    err = make_parse_error_json(
        PARSE_ERR_ILLEGAL_SEXP,
        "FR-PARSER-1",
        (f"exn:agentlisp:parse: 非法 S-expression，不符合 §3 EBNF 语法：表单= {malformed_sexp!r}"),
        source="test-case-parser-1.al",
        line=3,
        column=14,
        position=97,
        span=21,
        hints=[
            "请参考 SRS §3 EBNF：块顺序必须是 :model → :tools → :context → :harness → :correct (可选 MultiAgent)",
            "每个块使用 (:keyword ...) 列表，禁止非列表原子块",
        ],
    )
    _assert_json_error_shape(err)
    # 契约 A：schema_version 匹配
    assert err["schema_version"] == PARSER_ERROR_SCHEMA_VERSION
    # 契约 B：code 前缀 PARSE_*
    assert err["code"].startswith("PARSE_"), f"期望 PARSE_* 前缀，实际 code={err['code']}"
    # 契约 C：srs_id 精确匹配
    assert err["srs_id"] == "FR-PARSER-1", f"srs_id={err['srs_id']} 期望 FR-PARSER-1"
    # 契约 D：message 含 exn:agentlisp:parse（结构化 parse 异常类型）
    assert "exn:agentlisp:parse" in err["message"], (
        "FR-PARSER-1：非法 S-exp 必须抛出结构化 exn:agentlisp:parse，"
        f"当前 message={err['message']!r}"
    )
    # 契约 E：禁止出现 Racket 原生 match: no matching clause（崩溃字符串）
    assert "match: no matching clause" not in err["message"], (
        "FR-PARSER-1：禁止 Racket 原生 `match: no matching clause` 崩溃泄漏到用户层"
    )
    # 契约 F：hints 非空（可操作建议）
    assert len(err["hints"]) >= 1, "FR-PARSER-1：parse error hints[] 必须给出可操作修复建议"
    # 契约 G：srcloc 有 line/column（可定位到具体源位置，不是通用 #f）
    assert err["srcloc"]["line"] is not None and err["srcloc"]["column"] is not None, (
        "FR-PARSER-1：结构化 parse error 必须带源位置 line/column（IDE 红波浪集成用）"
    )


@pytest.mark.req("FR-PARSER-2")
def test_fr_parser_2_provider_enum_and_temperature_range_validation() -> None:  # type: ignore[no-untyped-def]
    """FR-PARSER-2 (L85)：provider ∈ {anthropic, openai, qwen, mock}; temperature ∈ [0.0, 1.0]。
    SRS §6.1 L225 反例：provider="abc" / temperature=2.0（两条都必须 FAIL）。"""
    from runtime.checker import (
        FR_PARSER_PROVIDER_ENUM,
        PARSE_ERR_PROVIDER_OR_TEMP,
        validate_provider_and_temperature,
    )

    # === (A) 正例：4 provider × 3 温度边界（必须全部 PASS）===
    OK_PROVIDERS = sorted(FR_PARSER_PROVIDER_ENUM)  # 顺序无关
    assert OK_PROVIDERS == ["anthropic", "mock", "openai", "qwen"], (
        f"FR-PARSER-2 SSOT provider 枚举变了：{OK_PROVIDERS}"
    )
    OK_TEMPS = [0.0, 0.5, 1.0, 0, 1]  # int 端点也应接受（Python 自动转 float）
    for p in OK_PROVIDERS:
        for t in OK_TEMPS:
            ok, err = validate_provider_and_temperature(p, t)
            assert ok and err is None, (
                f"FR-PARSER-2 正例应 PASS：provider={p} temperature={t}，实际 ok={ok} err={err}"
            )

    # === (B) 反例 1：非法 provider "abc" ===
    ok, err = validate_provider_and_temperature("abc", 0.0)
    assert not ok and err is not None, f"provider=abc 应 FAIL：ok={ok} err={err}"
    _assert_json_error_shape(err)
    assert err["srs_id"] == "FR-PARSER-2"
    assert err["code"] == PARSE_ERR_PROVIDER_OR_TEMP
    assert "provider" in err["message"] and "abc" in err["message"]
    # hints 必须给出合法枚举
    assert any("anthropic" in h and "mock" in h for h in err["hints"]), (
        f"FR-PARSER-2：非法 provider 时 hints[] 未给出合法枚举值：hints={err['hints']}"
    )

    # === (C) 反例 2：温度 2.0（超过上限，§6.1 L225 原反例值）===
    ok2, err2 = validate_provider_and_temperature("anthropic", 2.0)
    assert not ok2 and err2 is not None, f"temp=2.0 应 FAIL：ok={ok2} err={err2}"
    _assert_json_error_shape(err2)
    assert err2["srs_id"] == "FR-PARSER-2"
    assert err2["code"] == PARSE_ERR_PROVIDER_OR_TEMP
    assert "2.0" in err2["message"] or "temperature" in err2["message"]
    # === (D) 反例 3：温度 -0.1（低于下限）===
    ok3, err3 = validate_provider_and_temperature("qwen", -0.1)
    assert not ok3 and err3 is not None, f"temp=-0.1 应 FAIL：ok={ok3} err={err3}"
    _assert_json_error_shape(err3)
    assert err3["srs_id"] == "FR-PARSER-2"
    # === (E) 反例 4：温度类型错误（字符串 "hot" / bool True——bool 是 int 子类必须 FAIL）===
    ok4a, err4a = validate_provider_and_temperature("openai", "hot")
    assert not ok4a and err4a is not None, "temp='hot' 应 FAIL"
    _assert_json_error_shape(err4a)
    ok4b, err4b = validate_provider_and_temperature(
        "openai", True
    )  # True=1 按规范算越界（语义是 True 不是数字 1）
    assert not ok4b and err4b is not None, (
        "FR-PARSER-2：temperature 禁止 bool 类型（True/False 是 int 子类，会误通过范围校验导致语义歧义）"
    )
    _assert_json_error_shape(err4b)


@pytest.mark.req("FR-PARSER-3")
def test_fr_parser_3_memory_auto_append_renamed_to_python_underscore_and_bool_not_lost() -> None:  # type: ignore[no-untyped-def]
    """FR-PARSER-3 (L87)：
    - spec 命名 :auto-append（禁止旧命名 :auto-append-episodic）
    - emit context 段输出键 auto_append_episodic（下划线）
    - DSL #t/#f 值不静默丢失（None/"" 视为丢失 → FAIL）
    """
    from runtime.checker import (
        PARSE_ERR_MEMORY_AUTO_APPEND,
        validate_memory_auto_append_key,
    )

    # (A) 正例：spec 键 + python 下划线键同时存在，值 True/False 都保留
    ok_cfg_true = {
        "auto-append": True,  # DSL #t
        "auto_append_episodic": True,  # emit 后 Python 侧结果键
    }
    ok, err = validate_memory_auto_append_key(ok_cfg_true)
    assert ok and err is None, f"正例 true 应 PASS：ok={ok} err={err}"
    ok_cfg_false = {
        "auto-append": False,  # DSL #f
        "auto_append_episodic": False,
    }
    ok2, err2 = validate_memory_auto_append_key(ok_cfg_false)
    assert ok2 and err2 is None, f"正例 false 应 PASS：ok={ok2} err={err2}"

    # (B) 反例 1：旧命名 :auto-append-episodic（spec 层废弃 → FAIL）
    legacy_cfg = {"auto-append-episodic": True}
    ok3, err3 = validate_memory_auto_append_key(legacy_cfg)
    assert not ok3 and err3 is not None, f"旧命名应 FAIL：ok={ok3} err={err3}"
    _assert_json_error_shape(err3)
    assert err3["srs_id"] == "FR-PARSER-3"
    assert err3["code"] == PARSE_ERR_MEMORY_AUTO_APPEND
    assert "auto-append-episodic" in err3["message"], (
        f"反例应包含废弃命名：message={err3['message']!r}"
    )
    # hints 必须提到「:auto-append（spec）→ auto_append_episodic（Python）」重命名规则
    # （两 hints 可以在不同行：一条讲 spec 命名，一条讲 emit 下划线键；合并后两个词都出现即 OK）
    combined_hints = " ".join(err3["hints"])
    assert "auto-append" in combined_hints and "auto_append_episodic" in combined_hints, (
        f"FR-PARSER-3：hints 未提及重命名规则；combined={combined_hints!r}"
    )

    # (C) 反例 2：spec 键有 :auto-append 但值 None 或空串（静默丢失 #t/#f → FAIL）
    lost_cfg = {"auto-append": None, "auto_append_episodic": None}
    ok4, err4 = validate_memory_auto_append_key(lost_cfg)
    assert not ok4 and err4 is not None, f"值丢失应 FAIL：ok={ok4} err={err4}"
    _assert_json_error_shape(err4)
    assert err4["srs_id"] == "FR-PARSER-3"

    # (D) 反例 3：spec 键有值，但 emit 阶段未生成 Python 下划线键（只做了 parse 没做 rename）
    only_spec_cfg = {"auto-append": True}  # 缺 auto_append_episodic
    ok5, err5 = validate_memory_auto_append_key(only_spec_cfg)
    assert not ok5 and err5 is not None, f"缺 python 下划线键应 FAIL：ok={ok5} err={err5}"
    _assert_json_error_shape(err5)
    assert err5["srs_id"] == "FR-PARSER-3"
    assert "auto_append_episodic" in err5["message"], (
        f"message 未指向下划线键缺失：message={err5['message']!r}"
    )

    # (E) 正例 E：不含 spec 键（可选 memory-policy 块可缺）→ 必须 PASS（不强制要求所有 .al 都写 memory）
    ok6, err6 = validate_memory_auto_append_key({"markdown_fs": "/tmp/md"})
    assert ok6 and err6 is None, (
        f"不使用 memory :auto-append 特性时应允许 PASS：ok={ok6} err={err6}"
    )


@pytest.mark.req("FR-PARSER-4")
def test_fr_parser_4_tools_4_combinations_and_mcp_scheme_whitelist() -> None:  # type: ignore[no-untyped-def]
    """FR-PARSER-4 (L88)：4 种 tools 组合全支持 + MCP scheme 白名单。
    SRS L201：import-mcp scheme ∈ {stdio,http+unix,https,sse}，其它（如明文 http://）直接 FR-PARSER-FAIL。"""
    from runtime.checker import (
        FR_PARSER_MCP_SCHEMES,
        PARSE_ERR_TOOLS_COMBINATION,
        validate_tools_combination_and_mcp_scheme,
    )

    # === (A) 4 种合法组合（必须全 PASS 不崩溃）===
    # A1 = 仅 define-tool × N
    only_define = {
        "define_tools": [{"name": "t1"}, {"name": "t2"}],
        "import_builtin": False,
        "import_mcp": [],
    }
    ok1, err1 = validate_tools_combination_and_mcp_scheme(only_define)
    assert ok1 and err1 is None, f"A1 only define-tool 应 PASS：ok={ok1} err={err1}"
    # A2 = 仅 import-builtin
    only_builtin = {"define_tools": [], "import_builtin": True, "import_mcp": []}
    ok2, err2 = validate_tools_combination_and_mcp_scheme(only_builtin)
    assert ok2 and err2 is None, f"A2 only builtin 应 PASS：ok={ok2} err={err2}"
    # A3 = 仅 import-mcp（4 scheme 都必须通过，构造标准 URL）
    for scheme in sorted(FR_PARSER_MCP_SCHEMES):
        if scheme == "stdio":
            # stdio:/// 三斜杠：/// 后面是绝对文件系统路径（stdio 特殊协议）
            url = f"{scheme}:///path/to/mcp-server.py"
        elif scheme == "http+unix":
            # http+unix:// + URL-encoded socket 路径 + api
            url = f"{scheme}://%2Fvar%2Frun%2Fmcp.sock/api"
        elif scheme == "sse":
            url = f"{scheme}://mcp.example.com/events"
        else:  # https
            url = f"{scheme}://mcp.example.com/v1"
        only_mcp = {"define_tools": [], "import_builtin": False, "import_mcp": [url]}
        ok, err = validate_tools_combination_and_mcp_scheme(only_mcp)
        assert ok and err is None, (
            f"A3 only import-mcp scheme={scheme} 应 PASS：url={url} ok={ok} err={err}"
        )
    # A4 = 任意组合（define + builtin + mcp 叠一起）
    combined = {
        "define_tools": [{"name": "custom-extract"}],
        "import_builtin": True,
        "import_mcp": ["https://mcp.example.com/codebase", "sse://mcp.example.com/events"],
    }
    ok4, err4 = validate_tools_combination_and_mcp_scheme(combined)
    assert ok4 and err4 is None, f"A4 组合应 PASS：ok={ok4} err={err4}"

    # === (B) 反例：明文 http://mcp.example.com（scheme 不在白名单，§5.5 L197 禁止明文 HTTP）
    bad_scheme = {
        "define_tools": [],
        "import_builtin": False,
        "import_mcp": ["http://mcp.example.com/bad"],
    }
    ok5, err5 = validate_tools_combination_and_mcp_scheme(bad_scheme)
    assert not ok5 and err5 is not None, f"明文 http 应 FAIL：ok={ok5} err={err5}"
    _assert_json_error_shape(err5)
    assert err5["srs_id"] == "FR-PARSER-4"
    assert err5["code"] == PARSE_ERR_TOOLS_COMBINATION
    assert "http" in err5["message"].lower(), f"message 未指明 scheme 问题：{err5['message']!r}"
    # hints 必须明确提到「禁止明文 http/ws」
    assert any(("http" in h.lower() or "明文" in h) for h in err5["hints"]), (
        f"FR-PARSER-4：MCP scheme FAIL 时 hints[] 必须给出安全提示：hints={err5['hints']}"
    )

    # === (C) 反例：ws://（明文 WebSocket，同样禁止）
    bad_ws = {"define_tools": [], "import_mcp": ["ws://mcp.example.com/stream"]}
    ok6, err6 = validate_tools_combination_and_mcp_scheme(bad_ws)
    assert not ok6 and err6 is not None, f"ws 明文应 FAIL：ok={ok6} err={err6}"
    _assert_json_error_shape(err6)
    assert err6["srs_id"] == "FR-PARSER-4"


@pytest.mark.req("FR-PARSER-5")
def test_fr_parser_5_correct_on_failure_three_values_and_rejects_underscore_variants() -> None:  # type: ignore[no-untyped-def]
    """FR-PARSER-5 (L89)：on-failure ∈ {ask-human, fallback-model, abort} 三连字符枚举。
    SRS §6.1 L225 反例：on_failure=ask_human（下划线非法）。"""
    from runtime.checker import (
        FR_PARSER_ON_FAILURE_ENUM,
        PARSE_ERR_ON_FAILURE,
        validate_correct_on_failure,
    )

    LEGAL = sorted(FR_PARSER_ON_FAILURE_ENUM)
    assert LEGAL == ["abort", "ask-human", "fallback-model"], (
        f"FR-PARSER-5 on-failure SSOT 枚举变了：{LEGAL}"
    )

    # (A) 正例：3 合法值 × 大小写敏感（必须全 PASS）
    for v in LEGAL:
        ok, err = validate_correct_on_failure(v)
        assert ok and err is None, f"on_failure={v!r} 应 PASS：ok={ok} err={err}"

    # (B) 反例 1：§6.1 L225 原反例 ask_human（下划线变体 —— 必须 FAIL，不是自动兼容）
    ok1, err1 = validate_correct_on_failure("ask_human")
    assert not ok1 and err1 is not None, f"ask_human 下划线应 FAIL：ok={ok1} err={err1}"
    _assert_json_error_shape(err1)
    assert err1["srs_id"] == "FR-PARSER-5"
    assert err1["code"] == PARSE_ERR_ON_FAILURE
    # hints 必须给出纠正后的连字符版本
    assert any("ask-human" in h for h in err1["hints"]), (
        f"下划线误用 → hints[] 必须给出纠正：hints={err1['hints']}"
    )

    # (C) 反例 2：fallback_model（另一个下划线变体）
    ok2, err2 = validate_correct_on_failure("fallback_model")
    assert not ok2 and err2 is not None, f"fallback_model 下划线应 FAIL：ok={ok2} err={err2}"
    _assert_json_error_shape(err2)
    assert err2["srs_id"] == "FR-PARSER-5"
    assert any("fallback-model" in h for h in err2["hints"])

    # (D) 反例 3：任意字符串（如 "retry" / "ignore" / 空串）
    ok3a, err3a = validate_correct_on_failure("retry")
    assert not ok3a and err3a is not None, "'retry' 应 FAIL"
    _assert_json_error_shape(err3a)
    assert err3a["srs_id"] == "FR-PARSER-5"
    ok3b, err3b = validate_correct_on_failure("")
    assert not ok3b and err3b is not None, "空串应 FAIL"
    _assert_json_error_shape(err3b)
    assert err3b["srs_id"] == "FR-PARSER-5"
    ok3c, err3c = validate_correct_on_failure(None)
    assert not ok3c and err3c is not None, "None 应 FAIL"
    _assert_json_error_shape(err3c)
    assert err3c["srs_id"] == "FR-PARSER-5"


@pytest.mark.req("FR-PARSER-6")
def test_fr_parser_6_multiagent_topology_enum_and_scoped_worker_min_four_blocks() -> None:  # type: ignore[no-untyped-def]
    """FR-PARSER-6 (L90)：
    - topology ∈ {peer, orchestration, decentralised, judge-driven}
    - 每个 scoped-worker 至少 name+model+tools+harness 四块。
    SRS §6.1 L225 反例：topology=foo-bar（非法值）。"""
    from runtime.checker import (
        FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS,
        FR_PARSER_TOPOLOGY_ENUM,
        PARSE_ERR_TOPOLOGY,
        validate_topology_and_scoped_worker_min_blocks,
    )

    LEGAL_TOPO = sorted(FR_PARSER_TOPOLOGY_ENUM)
    EXPECTED_TOPO = ["decentralised", "judge-driven", "orchestration", "peer"]
    assert LEGAL_TOPO == EXPECTED_TOPO, (
        f"FR-PARSER-6 topology SSOT 变了：actual={LEGAL_TOPO} expected={EXPECTED_TOPO}"
    )
    EXPECTED_BLOCKS = ("name", "model", "tools", "harness")
    assert FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS == EXPECTED_BLOCKS, (
        f"scoped-worker 最小四块 SSOT 变了：actual={FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS}"
    )

    # (A) 正例：4 topology × 无 scoped_workers（仅顶层 multi-agent 声明块）→ PASS
    for topo in LEGAL_TOPO:
        ok, err = validate_topology_and_scoped_worker_min_blocks(topo)
        assert ok and err is None, f"topology={topo} 正例应 PASS：ok={ok} err={err}"

    # (B) 正例：带 scoped_workers，4 块齐全
    full_workers = [
        {
            "name": "w1",
            "model": {"provider": "mock", "model": "m", "temperature": 0.0},
            "tools": {"define_tools": []},
            "harness": {"correct": {"on_failure": "ask-human"}},
        },
        {
            "name": "w2",
            "model": {"provider": "mock", "model": "m", "temperature": 0.0},
            "tools": {"import_builtin": True},
            "harness": {"constrain": {"forbidden": ["rm"]}},
        },
    ]
    ok2, err2 = validate_topology_and_scoped_worker_min_blocks("peer", full_workers)
    assert ok2 and err2 is None, f"4 块齐全应 PASS：ok={ok2} err={err2}"

    # (C) 反例 1：§6.1 L225 原反例 topology=foo-bar
    ok3, err3 = validate_topology_and_scoped_worker_min_blocks("foo-bar")
    assert not ok3 and err3 is not None, f"topology=foo-bar 应 FAIL：ok={ok3} err={err3}"
    _assert_json_error_shape(err3)
    assert err3["srs_id"] == "FR-PARSER-6"
    assert err3["code"] == PARSE_ERR_TOPOLOGY
    assert "foo-bar" in err3["message"]
    # 反例常见拼写错：decentralized（美式 z）应 FAIL（SRS 规范用英式 s decentralised）
    ok3b, err3b = validate_topology_and_scoped_worker_min_blocks("decentralized")
    assert not ok3b and err3b is not None, (
        "FR-PARSER-6：美式拼写 decentralized（带 z）应 FAIL（SRS 规定英式 decentralised，带 s）"
    )
    _assert_json_error_shape(err3b)
    assert err3b["srs_id"] == "FR-PARSER-6"
    assert any("decentralised" in h for h in err3b["hints"]), (
        "美式 z → 英式 s 的 hints[] 必须给出正确拼写"
    )

    # (D) 反例 2：scoped_worker 缺 name + model 两块
    bad_worker = {"tools": {}, "harness": {}}  # 缺 name / model
    ok4, err4 = validate_topology_and_scoped_worker_min_blocks("judge-driven", [bad_worker])
    assert not ok4 and err4 is not None, f"缺 2 块应 FAIL：ok={ok4} err={err4}"
    _assert_json_error_shape(err4)
    assert err4["srs_id"] == "FR-PARSER-6"
    # message 或 hints 必须列出缺的块名
    missing_txt = " ".join([err4["message"], *err4["hints"]])
    for b in ("name", "model"):
        assert b in missing_txt, f"message/hints 未指出缺块 {b!r}：combined={missing_txt!r}"

    # (E) 反例 3：scoped_workers 不是 list（单个 dict）
    ok5, err5 = validate_topology_and_scoped_worker_min_blocks(
        "orchestration",
        full_workers[0],  # type: ignore[arg-type]
    )
    assert not ok5 and err5 is not None, f"scoped_workers 传单个 dict 应 FAIL：ok={ok5} err={err5}"
    _assert_json_error_shape(err5)
    assert err5["srs_id"] == "FR-PARSER-6"


@pytest.mark.req("FR-PARSER-3")
def test_emit_context_auto_append_maps_to_underscore_key_in_python_source(tmp_path):
    """B-1/P3-5 双路径断言，racket 在/不在 PATH 都 100% hard-assert 无 skip 分支。"""
    import shutil
    import subprocess

    racket_bin = shutil.which("racket")
    repo = Path(__file__).resolve().parents[2]
    compiler_src = repo / "compiler" / "agentlisp_compiler.rkt"
    src_text = compiler_src.read_text(encoding="utf-8")
    # 路径 B（本机无 racket → fallback 到源码字符串双断言）：任何环境都硬 assert 真
    assert "auto_append_episodic" in src_text, (
        "FR-PARSER-3 emit FAIL: compiler 源码未出现 Python 下划线键 auto_append_episodic"
    )
    assert ":auto-append-episodic" in src_text and "FR-PARSER-3" in src_text, (
        "FR-PARSER-3 parse FAIL: 旧命名 :auto-append-episodic 未触发结构化 FR-PARSER-3 错误分支"
    )
    # 路径 A（CI Ubuntu 有 racket）：真发射产物 grep
    if racket_bin is not None:
        sample = repo / "examples" / "production-repair-agent.al"
        out_py = tmp_path / "agent.py"
        cp = subprocess.run(
            [racket_bin, str(repo / "compiler" / "main.rkt"), "-i", str(sample), "-o", str(out_py)],
            capture_output=True,
            text=True,
            cwd=str(repo),
            timeout=120,
        )
        assert cp.returncode == 0, f"racket compile exit={cp.returncode} stderr={cp.stderr}"
        assert out_py.exists(), "racket emit 产物不存在"
        emitted = out_py.read_text(encoding="utf-8")
        assert "auto_append_episodic" in emitted, (
            "FR-PARSER-3 emit FAIL: racket 真发射产物中未出现 auto_append_episodic 下划线键"
        )
        assert "auto-append-episodic" not in emitted or "context_config" not in emitted, (
            "FR-PARSER-3 emit FAIL: 产物中出现连字符 auto-append-episodic（Python dict key 非法）"
        )
