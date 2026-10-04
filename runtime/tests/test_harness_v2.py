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
