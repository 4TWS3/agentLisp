"""
AgentLisp v2.0 合并版 Harness 基类（runtime/base_harness_v2.py）

修复对象：
  A = runtime/base_harness.py (通用 ReAct + Evidence 链 + Checkpoint)
  B = runtime/base_agent_harness.py (四参 constructor + KV Cache 四段 + 三重管道)

修复问题（Code Review Issue 1-5，全部 high confidence）：
  1. step 硬编码 mock tool/observation → 改为 llm_client Protocol + tool_registry 驱动
  2. 缺证据链 → 引入 ExecutionTrace / ReActTurn.duration_ms / final_answer / status
  3. Status Bar 用 user 角色污染对话 → 改为独立 system 角色的 <agent_status> 段
  4. constrain substring 误杀 → 正则词边界 \b + shlex token 精确匹配
  5. 缺 Checkpoint / StatusBar Hook → 把 MemoryCheckpointStore + StatusBar Protocol 注入 step() 的 on_start / on_step / on_done

对外稳定接口（Emitter 生成产物继承此类）：
  class BaseHarnessV2(BaseAgentHarnessProtocol, StatusBarReceiverProtocol, CheckpointAwareProtocol):
      def __init__(self,
                   model_config: Dict[str, Any],
                   context_config: Dict[str, Any],
                   tools_config: Dict[str, Any],
                   harness_config: Dict[str, Any],
                   *,
                   llm_client: Optional["LLMClientProtocol"] = None,
                   tool_registry: Optional["ToolRegistryProtocol"] = None,
                   checkpoint_store: Optional["CheckpointStoreProtocol"] = None,
                   status_bar: Optional["StatusBarProtocol"] = None,
                   max_turns: int = 30,
                   react_mode: bool = True)
      async def run(self, user_input: str) -> "ExecutionTrace"
      async def step(self, user_input: Optional[str] = None) -> Dict[str, Any]
"""

from __future__ import annotations

import asyncio
import contextlib
import gc
import logging
import pathlib
import re
import shlex
import time
import uuid
from collections.abc import AsyncIterator, Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import (
    Any,
    Protocol,
    runtime_checkable,
)

logger = logging.getLogger(__name__)

# Python-side SSOT mirror of compiler/checker.rkt SIDEEFFECT-BUILTIN-TOOLS (L87).
# BaseHarnessV2.constrain() uses this set to enforce FR-CHECK-2 invariant
# at runtime even when the compiled emit bypasses the Racket static checker.
try:
    from runtime.checker import SIDEEFFECT_BUILTIN_TOOLS
except Exception:  # pragma: no cover - extremely rare (broken package)
    SIDEEFFECT_BUILTIN_TOOLS = frozenset(  # type: ignore[assignment]
        {"bash", "git-push", "wget", "curl", "scp", "dd", "chmod", "sudo"}
    )

# ==============================================================================
# 证据链数据结构 (对应 Code Review Issue #2)
# ==============================================================================


@dataclass
class ReActTurnV2:
    index: int
    thought: str | None = None
    action: str | None = None
    action_input: dict[str, Any] | None = None
    observation: Any | None = None
    answer: str | None = None
    status: str = "pending"  # pending / success / failed / blocked / retry
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None

    @property
    def duration_ms(self) -> int:
        if self.finished_at is None:
            return 0
        return int((self.finished_at - self.started_at) * 1000)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["duration_ms"] = self.duration_ms
        return d


@dataclass
class ExecutionTraceV2:
    run_id: str
    agent_name: str | None
    started_at: datetime
    finished_at: datetime | None = None
    turns: list[ReActTurnV2] = field(default_factory=list)
    final_answer: str | None = None
    status: str = "pending"  # pending / running / success / failed / blocked / human_required
    error: str | None = None

    @property
    def duration_ms(self) -> int:
        if self.finished_at is None:
            return 0
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "turns": [t.to_dict() for t in self.turns],
            "final_answer": self.final_answer,
            "error": self.error,
        }


# ==============================================================================
# 外部依赖 Protocol（避免 import 时硬绑定可选依赖）
# ==============================================================================


@runtime_checkable
class LLMClientProtocol(Protocol):
    async def achat(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]: ...


@runtime_checkable
class ToolRegistryProtocol(Protocol):
    async def acall(self, name: str, **kwargs: Any) -> Any: ...
    def names(self) -> list[str]: ...
    def to_openai_schema(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class CheckpointStoreProtocol(Protocol):
    async def save(self, key: str, payload: dict[str, Any]) -> None: ...
    async def load(self, key: str) -> dict[str, Any] | None: ...


@runtime_checkable
class StatusBarProtocol(Protocol):
    def on_start(self, run_id: str, agent_name: str | None) -> None: ...
    def on_step(
        self, run_id: str, turn_index: int, event: str, detail: Any | None = None
    ) -> None: ...
    def on_done(
        self, run_id: str, status: str, final_answer: str | None, error: str | None
    ) -> None: ...


# ==============================================================================
# Memory 版默认实现（零依赖，对应 runtime/checkpoint.py / status_bar.py 子集）
# ==============================================================================


class _MemoryCheckpointStore:
    """仅在外部未注入 checkpoint_store 时使用，对应 runtime.checkpoint.MemoryCheckpointStore 的最小形态。"""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    async def save(self, key: str, payload: dict[str, Any]) -> None:
        self._data[key] = payload

    async def load(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key)


class _PrintingStatusBar:
    """仅在外部未注入 status_bar 时使用。"""

    def on_start(self, run_id: str, agent_name: str | None) -> None:
        logger.info("[StatusBar] on_start run_id=%s agent=%s", run_id, agent_name)

    def on_step(self, run_id: str, turn_index: int, event: str, detail: Any | None = None) -> None:
        logger.info("[StatusBar] on_step run_id=%s turn=%s event=%s", run_id, turn_index, event)

    def on_done(
        self, run_id: str, status: str, final_answer: str | None, error: str | None
    ) -> None:
        logger.info(
            "[StatusBar] on_done run_id=%s status=%s final_answer=%s error=%s",
            run_id,
            status,
            final_answer,
            error,
        )


# ==============================================================================
# Constrain 词边界匹配 (对应 Code Review Issue #4)
# ==============================================================================


_FORBIDDEN_WORD_BOUNDARY_RE = re.compile(
    r"(?<!\w)rm(?!\w)"
)  # placeholder（实际由 _forbidden_regex 动态生成）


def _forbidden_regex(pattern: str) -> re.Pattern[str]:
    """把 forbidden 字符串编译为词边界精确匹配（避免 rm 匹配 rmtree / cat 匹配 category）。"""
    escaped = re.escape(pattern.strip())
    return re.compile(rf"(?<![A-Za-z0-9_./-]){escaped}(?![A-Za-z0-9_./-])")


def _contains_forbidden_token(command: str, forbidden: str) -> bool:
    """优先 shlex token 精确匹配（bash 场景），fallback 正则词边界。"""
    if not command or not forbidden:
        return False
    # token 级匹配（优先）
    try:
        tokens = shlex.split(command, comments=True, posix=True)
    except ValueError:
        tokens = []
    if tokens:
        forbidden_tokens = forbidden.split()
        n = len(forbidden_tokens)
        if n == 1:
            if forbidden_tokens[0] in tokens:
                return True
        else:
            for i in range(len(tokens) - n + 1):
                if tokens[i : i + n] == forbidden_tokens:
                    return True
    # fallback：正则词边界
    return bool(_forbidden_regex(forbidden).search(command))


def _normalize_pure_posix_parts(path: pathlib.PurePosixPath) -> pathlib.PurePosixPath:
    """对 PurePosixPath 的 parts 手工规范化，去掉 `.` / `..`（纯字符串运算，不调用真实文件系统的 resolve()）。"""
    parts = list(path.parts)
    stack: list[str] = []
    for p in parts:
        if p == ".":
            continue
        if p == "..":
            # 非空且顶部不是根 "/" 才能弹；已是根的话保持根（不吞掉）
            if stack and stack[-1] != "/":
                stack.pop()
            continue
        stack.append(p)
    if not stack:
        return pathlib.PurePosixPath(".")
    if len(stack) == 1 and stack[0] == "/":
        return pathlib.PurePosixPath("/")
    return pathlib.PurePosixPath(*stack)


# ==============================================================================
# 上下文组装 (对应 Code Review Issue #3：Status Bar 改用 system 角色)
# ==============================================================================


def build_kv_aligned_context(
    *,
    system_prompt: str,
    tools_schema_text: str | None = None,
    tools_openai_schema: list[dict[str, Any]] | None = None,
    trajectory: list[dict[str, Any]],
    step_count: int,
    status_bar_config: dict[str, Any],
    terminated: bool = False,
    extra_status_items: dict[str, Any] | None = None,
    mounted_layers: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    KV Cache 严格四段+1 memory 段 (对应 base_agent_harness.build_context 的规范固化版)：

      (1) Static System Prompt          → role=system（稳定，命中供应商 Prefix Cache）
      (1.5) [Memory] mounted layers 段   → role=system（SRS FR-MEM-1：有 markdown_fs 时追加）
      (2) Static Tools Schema           → role=system（稳定，命中供应商 Prefix Cache）
      (3) Dynamic Trajectory            → role=user/assistant/tool（每回合追加）
      (4) Trailing Status Bar Hook      → role=system（修正 Code Review #3：不再用 user 污染）

    tools_schema_text 与 tools_openai_schema 至少给其一；二者都给时 system 消息合并呈现。
    mounted_layers 非空时，在 system prompt 后追加 [Memory] mounted layers: x, y, z 段（SRS FR-MEM-1）。
    """
    messages: list[dict[str, Any]] = []

    # (1) Static System Prompt
    if not system_prompt:
        system_prompt = "You are a helpful Agent."
    messages.append({"role": "system", "content": system_prompt})

    # (1.5) [Memory] mounted layers: SRS FR-MEM-1（emitter 在 markdown_fs 非空时自动传入）
    if mounted_layers:
        layers_text = ", ".join(str(layer) for layer in mounted_layers if str(layer).strip())
        if layers_text:
            messages.append(
                {
                    "role": "system",
                    "content": f"[Memory] mounted layers: {layers_text}",
                }
            )

    # (2) Static Tools Schema
    tools_parts: list[str] = []
    if tools_schema_text:
        tools_parts.append(tools_schema_text.strip())
    if tools_openai_schema:
        import json as _json

        tools_parts.append(
            "OpenAI tools schema:\n"
            + _json.dumps(tools_openai_schema, ensure_ascii=False, indent=2)
        )
    if tools_parts:
        messages.append(
            {
                "role": "system",
                "content": "<tools_definition>\n"
                + "\n\n".join(tools_parts)
                + "\n</tools_definition>",
            }
        )

    # (3) Dynamic Trajectory
    messages.extend(trajectory)

    # (4) Status Bar (system 角色，修正 Issue #3)
    sb = status_bar_config or {}
    if sb:
        items: list[str] = []
        if sb.get("step_count", True):
            items.append(f"Step: {step_count}")
        items.append(f"Status: {'Terminated' if terminated else 'Active'}")
        if extra_status_items:
            for k, v in extra_status_items.items():
                items.append(f"{k}: {v}")
        if items:
            messages.append(
                {
                    "role": "system",
                    "content": "<agent_status>" + " | ".join(items) + "</agent_status>",
                }
            )

    return messages


# ==============================================================================
# Mock LLM Client（默认零依赖，用于本地单测或未安装 llm 组场景）
# ==============================================================================


class MockLLMClient:
    """按序返回 responses；若 responses 耗尽则返回终止回答。用于 Issue #1 的默认 LLM 注入。"""

    def __init__(self, responses: Iterable[dict[str, Any]] | None = None) -> None:
        import collections

        self._queue: collections.deque[dict[str, Any]] = collections.deque(
            responses
            or [
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-mock",
                            "type": "function",
                            "function": {"name": "echo", "arguments": {"message": "hello"}},
                        }
                    ],
                },
                {"role": "assistant", "content": "OK, done."},
            ]
        )

    async def achat(self, messages: list[dict[str, Any]], **_: Any) -> dict[str, Any]:
        if self._queue:
            return dict(self._queue.popleft())
        return {"role": "assistant", "content": "[MockLLM depleted] Task finished."}


# ==============================================================================
# Harness 基类
# ==============================================================================


class BaseHarnessV2:
    """
    AgentLisp v2 合并版 Harness：
      - 四参 constructor（B 版接口）+ 可选依赖注入（A 版能力）
      - KV Cache 四段 (build_kv_aligned_context)
      - 三重管道 Constrain / Verify / Correct
      - 证据链 ExecutionTraceV2 + turns[].duration_ms
      - Checkpoint / StatusBar Hook 全生命周期
    """

    def __init__(
        self,
        model_config: dict[str, Any],
        context_config: dict[str, Any],
        tools_config: dict[str, Any],
        harness_config: dict[str, Any],
        *,
        llm_client: LLMClientProtocol | None = None,
        tool_registry: ToolRegistryProtocol | None = None,
        checkpoint_store: CheckpointStoreProtocol | None = None,
        status_bar: StatusBarProtocol | None = None,
        max_turns: int = 30,
        react_mode: bool = True,
        agent_name: str | None = None,
        # CR-16 P1-5 Provider enum / CircuitBreaker（显式传入参数（CI可控）：
        llm_provider_orchestrator: Any | None = None,
        llm_fallback_provider: Any | None = None,
        llm_circuit_breaker: Any | None = None,
    ) -> None:
        self.model_config = dict(model_config or {})
        self.context_config = dict(context_config or {})
        self.tools_config = dict(tools_config or {})
        self.harness_config = dict(harness_config or {})

        # CR-16：Provider 层（FR-PARSER-2 + FR-CORRECT-2）：
        #   - llm_provider_orchestrator 显式传入时直接用；
        #   - 否则在 Model Harness Builder 模式（默认）用 llm_client 做 achat。
        self._llm_orchestrator = llm_provider_orchestrator
        self._fallback_provider = llm_fallback_provider
        self._circuit_breaker = llm_circuit_breaker

        self.llm_client: LLMClientProtocol = llm_client or MockLLMClient()  # Fix Issue #1
        self.tool_registry: ToolRegistryProtocol | None = tool_registry
        self.checkpoint_store: CheckpointStoreProtocol = (
            checkpoint_store or _MemoryCheckpointStore()
        )  # Fix Issue #5
        self.status_bar: StatusBarProtocol = status_bar or _PrintingStatusBar()  # Fix Issue #5

        self.max_turns = int(max_turns)
        self.react_mode = bool(react_mode)
        self.agent_name = agent_name or self.model_config.get("agent_name")

        # 运行时状态
        self.trajectory: list[dict[str, Any]] = []
        self.step_count: int = 0
        self.is_terminated: bool = False
        self._trace: ExecutionTraceV2 | None = None

        # SRS FR-MEM-1：若 context_config 指定 markdown_fs 或 layers，则自动创建 self.memory_fs 并挂载三层占位
        # emitter 生成代码时会进一步覆盖为具体 layers；测试端可手工 setattr 注入
        self.memory_fs: Any | None = None
        self._mounted_layers: list[str] = []
        try:
            from .memory_fs import MemoryFS
        except Exception:
            MemoryFS = None  # type: ignore[assignment,misc]
        _ccfg = self.context_config
        _markdown_fs = (
            _ccfg.get("markdown_fs") or _ccfg.get("memory_path") or _ccfg.get("memory_root")
        )
        _layers_raw = _ccfg.get("layers") or _ccfg.get("memory_layers") or []
        _has_memory_hint = bool(_markdown_fs or _layers_raw)
        if _has_memory_hint and MemoryFS is not None:
            try:
                self.memory_fs = MemoryFS(namespace=self.agent_name or "default")
            except Exception:
                self.memory_fs = None
        # 规范化 layers：把字符串/符号格式统一成 [L0-Abstract, L1-Overview, L2-FullText] 顺序
        if _layers_raw:
            for layer in _layers_raw:
                s = str(layer).strip()
                if s and s not in self._mounted_layers:
                    self._mounted_layers.append(s)
        # emitter 生成代码时会显式调用 self.memory_fs.put 三层挂载占位；这里保守只注册 _mounted_layers，不做异步

        # SRS NFR-OBS-1：OTel tracer（observability 组有装时 create_tracer() 真用，否则 None 时跳过）
        self.otel_tracer: Any = None

    # ------------------------------------------------------------------
    # 对外入口：run / step
    # ------------------------------------------------------------------

    async def run(self, user_input: str) -> ExecutionTraceV2:
        run_id = str(uuid.uuid4())
        self._trace = ExecutionTraceV2(
            run_id=run_id,
            agent_name=self.agent_name,
            started_at=datetime.now(UTC),
            status="running",
        )
        self.trajectory = [{"role": "user", "content": user_input}]
        self.step_count = 0
        self.is_terminated = False
        self.status_bar.on_start(run_id, self.agent_name)
        await self._save_checkpoint()

        try:
            loop_result = await self._react_loop(user_input)
            if loop_result.get("status") == "blocked":
                self._trace.status = "blocked"
                self._trace.error = loop_result.get("reason")
                self.is_terminated = True
                return self._trace
            if loop_result.get("status") == "failed":
                self._trace.status = "failed"
                self._trace.error = (
                    loop_result.get("error") or loop_result.get("feedback") or "failed"
                )
                self.is_terminated = True
                return self._trace
            if loop_result.get("status") == "human_required":
                self._trace.status = "human_required"
                self.is_terminated = True
                return self._trace
            self._trace.status = "success"
            self._trace.final_answer = loop_result.get("final_answer")
            self.is_terminated = True
            return self._trace
        except Exception as exc:
            self._trace.status = "failed"
            self._trace.error = f"{type(exc).__name__}: {exc}"
            self.is_terminated = True
            raise
        finally:
            self._trace.finished_at = datetime.now(UTC)
            self.status_bar.on_done(
                self._trace.run_id, self._trace.status, self._trace.final_answer, self._trace.error
            )
            await self._save_checkpoint()

    async def step(self, user_input: str | None = None) -> dict[str, Any]:
        """单步驱动（保留 B 版 API）。"""
        if self._trace is None:
            # lazy 初始化一次 trace，保证单步驱动也有证据链
            run_id = str(uuid.uuid4())
            self._trace = ExecutionTraceV2(
                run_id=run_id,
                agent_name=self.agent_name,
                started_at=datetime.now(UTC),
                status="running",
            )
            self.status_bar.on_start(run_id, self.agent_name)
        if user_input:
            self.trajectory.append({"role": "user", "content": user_input})
        self.step_count += 1
        return await self._react_step()

    # ------------------------------------------------------------------
    # 三重控制流管道（保留 B 版接口 + 强化实现）
    # ------------------------------------------------------------------

    def constrain(self, tool_call: dict[str, Any]) -> tuple[bool, str]:
        """【护栏 1：Constrain】负面清单 + 词边界匹配 + workspace_root 路径门控（Fix Issue #4 + SRS FR-RUN-3）。

        CR-22 P3-2 强化：FR-CHECK-2 runtime 侧镜像 ERR_UNGUARDED_TOOL_EXECUTION
        静态 invariant。当 tool_name ∈ SIDEEFFECT_BUILTIN_TOOLS（bash/git-push/wget/curl/scp/dd/chmod/sudo）
        时，**同时** 满足 (A ∧ B) ∨ C 三者之一：
            A) constrain.require_human_approval 包含该工具名；
            B) constrain.forbidden_commands 至少 1 条非空；
            C) verify.{json_schema,linter_check,test_runner,reviewer_agent} 任一项 truthy。
        三都不满足 → 立即 Block，reason 开头 `Harness Blocked: FR-CHECK-2`（便于 CI 反推 SRS-ID）。
        """
        tool_name = str(tool_call.get("tool_name") or "")
        args: dict[str, Any] = tool_call.get("args", {}) or {}
        cmd: str = str(args.get("command", ""))
        # (a0) FR-CHECK-2 runtime side-effect 护栏（CR-22 P3-2）
        if tool_name and tool_name in SIDEEFFECT_BUILTIN_TOOLS:
            constrain_cfg = (
                (self.harness_config.get("constrain") or {})
                if isinstance(self.harness_config, dict)
                else {}
            )
            verify_cfg = (
                (self.harness_config.get("verify") or {})
                if isinstance(self.harness_config, dict)
                else {}
            )
            approval_list = [
                str(x)
                for x in (
                    constrain_cfg.get("require_human_approval")
                    or constrain_cfg.get("require_approval")
                    or []
                )
            ]
            forbidden_raw = list(constrain_cfg.get("forbidden_commands") or [])
            forbidden_nonempty = any(True for x in forbidden_raw if str(x).strip() != "")
            approved = tool_name in approval_list
            verify_any = any(
                bool(verify_cfg.get(k))
                for k in ("json_schema", "linter_check", "test_runner", "reviewer_agent")
            )
            if not ((approved and forbidden_nonempty) or verify_any):
                reason = (
                    "Harness Blocked: FR-CHECK-2(ERR_UNGUARDED_TOOL_EXECUTION) "
                    f"side-effect builtin {tool_name!r} requires guardrails: "
                    "either (require_human_approval lists tool AND forbidden_commands non-empty) "
                    "OR any verify.* flag is truthy. "
                    f"current require_human_approval={approval_list!r} "
                    f"forbidden_commands={forbidden_raw!r} verify={verify_cfg!r}."
                )
                logger.warning(
                    "[Constrain][FR-CHECK-2] tool=%r unguarded; reason=%s", tool_name, reason
                )
                return False, reason
        # (a) forbidden_commands 词边界匹配（Issue #4）
        forbidden_list = list(
            self.harness_config.get("constrain", {}).get("forbidden_commands", []) or []
        )
        for forbidden in forbidden_list:
            if _contains_forbidden_token(cmd, forbidden):
                logger.warning("[Constrain] blocked forbidden=%r in cmd=%r", forbidden, cmd)
                return False, f"Harness Blocked: Execution of {forbidden!r} is strictly forbidden."
        # (b) workspace_root 路径逃逸门控（SRS FR-RUN-3）：
        #     不只是 bash 的 command 参数，还要递归遍历 args 中所有字符串值：
        #       - 含 "/" / "." / ".." 的候选 token；
        #       - 像路径的参数名（path/paths/cwd/file/files/src/dst/target/output/dir/directory/root）；
        #     workspace_root 非空时，所有候选必须是 workspace_root 的后代。
        #
        #     判定策略（评审要求的"物理 resolve + 纯 posix 规范化双保险"）：
        #       1) Python 运行时真实路径存在 → 用 os.path.realpath / Path.resolve() 做物理规范化（解 symlink）后 is_relative_to；
        #       2) 不存在或非本机路径（例如容器里的路径，本地单测不真的创建目录）→ 用 _normalize_pure_posix_parts 纯字符串规范化后 is_relative_to；
        #       3) 任意一个命中逃逸 → 立即返回 WorkspaceEscape（不允许部分通过）。
        workspace_root = (self.harness_config.get("constrain", {}) or {}).get("workspace_root")
        if workspace_root:
            root_raw = str(workspace_root)
            path_candidates: list[str] = []
            # (b.1) 从 bash 的 command 拆 shlex（老路径）
            try:
                tokens_cmd = shlex.split(cmd, comments=True, posix=True) if cmd else []
            except ValueError:
                tokens_cmd = cmd.split() if cmd else []
            for token in tokens_cmd:
                if not token or token in {
                    "|",
                    "&&",
                    ";",
                    "||",
                    "&",
                    ">",
                    "<",
                    ">>",
                    "2>",
                    "1>",
                    "&>",
                }:
                    continue
                if not ("/" in token or token == "." or token.startswith("..")):
                    continue
                candidate = token.replace("file://", "")
                if candidate:
                    path_candidates.append(candidate)
            # (b.2) 递归 args dict 收集路径候选（带参数名语义）
            PATH_HINT_KEYS = {
                "path",
                "paths",
                "file",
                "files",
                "dir",
                "dirs",
                "directory",
                "directories",
                "target",
                "dst",
                "src",
                "root",
                "output",
                "cwd",
                "workspace",
                "mount",
                "source",
                "destination",
                "working_dir",
                "working_directory",
                "home",
            }

            def _walk(v: Any, key_hint: str | None) -> None:
                if isinstance(v, str):
                    s = v.replace("file://", "")
                    if key_hint and key_hint in PATH_HINT_KEYS:
                        # 参数名明确是路径：即使不含 "/" 也加入（相对路径 "./foo" / "foo.txt"）
                        path_candidates.append(s)
                        return
                    if "/" in s or s == "." or s.startswith(".."):
                        path_candidates.append(s)
                    return
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        _walk(vv, str(kk) if isinstance(kk, str) else None)
                    return
                if isinstance(v, (list, tuple, set)):
                    for item in v:
                        _walk(item, key_hint)
                    return

            for k, v in args.items():
                _walk(v, str(k) if isinstance(k, str) else None)
            # (b.3) 去重（保持顺序）
            seen: set = set()
            dedup: list[str] = []
            for s in path_candidates:
                if s in seen:
                    continue
                seen.add(s)
                dedup.append(s)
            # (b.4) 对每个候选做双保险规范化 + is_relative_to 判定
            root_pure = pathlib.PurePosixPath(root_raw)

            def _fs_resolve_if_exists(cand_path: str) -> pathlib.Path | None:
                """路径真实存在（或父目录存在可 resolve）→ 返回 Path.resolve(strict=False)；否则返回 None。"""
                try:
                    # 允许把非绝对的相对 root 先拼成绝对存在性检查
                    cp = pathlib.Path(cand_path)
                    if not cp.is_absolute():
                        cp = pathlib.Path(str(root_raw)) / cand_path
                    try:
                        if cp.exists() or cp.parent.exists():  # 存在 or 父存在 → 调真实 FS resolve
                            return cp.resolve(strict=False)
                    except (OSError, RuntimeError):
                        return None
                except Exception:
                    return None
                return None

            for candidate in dedup:
                try:
                    cand_pure = pathlib.PurePosixPath(candidate)
                except Exception:
                    continue
                if cand_pure.is_absolute():
                    resolved_pure = _normalize_pure_posix_parts(cand_pure)
                else:
                    resolved_pure = _normalize_pure_posix_parts(root_pure / cand_pure)
                escaped_pure = False
                try:
                    escaped_pure = not resolved_pure.is_relative_to(root_pure)
                except Exception:
                    escaped_pure = True
                if escaped_pure:
                    logger.warning(
                        "[Constrain][WorkspaceEscape-Pure] root=%r candidate=%r resolved=%r",
                        str(root_pure),
                        candidate,
                        str(resolved_pure),
                    )
                    return False, (
                        f"Harness Blocked: WorkspaceEscape: target path candidate {candidate!r} "
                        f"resolves to {str(resolved_pure)!r} escapes workspace_root={str(root_pure)!r}"
                    )
                # 物理 FS 层 resolve 再验一次（双保险）：存在就解 symlink，解后必须仍在 root 下
                fs_resolved = _fs_resolve_if_exists(candidate)
                if fs_resolved is not None:
                    root_fs = pathlib.Path(str(root_raw)).resolve(strict=False)
                    try:
                        if not fs_resolved.is_relative_to(root_fs):
                            logger.warning(
                                "[Constrain][WorkspaceEscape-FS] root=%r candidate=%r resolved_fs=%r",
                                str(root_fs),
                                candidate,
                                str(fs_resolved),
                            )
                            return False, (
                                f"Harness Blocked: WorkspaceEscape: filesystem-resolved path {candidate!r} "
                                f"→ {str(fs_resolved)!r} (symlink/realpath) escapes workspace_root={str(root_fs)!r}"
                            )
                    except Exception:
                        # is_relative_to 抛异常视为逃逸（可能是 path 类型不同等）
                        logger.warning(
                            "[Constrain][WorkspaceEscape-FS-exc] root=%r candidate=%r",
                            str(root_raw),
                            candidate,
                            exc_info=True,
                        )
                        return False, (
                            f"Harness Blocked: WorkspaceEscape: path {candidate!r} failed filesystem "
                            f"is_relative_to check against workspace_root={str(root_raw)!r}"
                        )
                # 再检查：真实 root 存在 + 候选绝对路径但 root 是 `/app/workspace`，候选是 `/app/workspacefoo` 时，PurePosix 仍可能误判？
                # PurePosixPath("/app/workspacefoo").is_relative_to("/app/workspace") 返回 False，所以无需再补
        return True, "OK"

    def verify(self, observation: dict[str, Any]) -> tuple[bool, str]:
        """【护栏 2：Verify】exit_code 静态断言；子类可 override 注入业务断言。"""
        if not isinstance(observation, dict):
            return True, "Verified (non-dict observation)"
        if observation.get("exit_code", 0) != 0:
            err_msg = str(
                observation.get("stderr") or observation.get("error") or "Execution failed"
            )
            logger.warning(
                "[Verify] failed exit_code=%s err=%s", observation.get("exit_code"), err_msg
            )
            return False, err_msg
        return True, "Verified"

    async def correct(
        self,
        tool_call: dict[str, Any],
        error_msg: str,
        retries: int,
    ) -> dict[str, Any]:
        """【护栏 3：Correct】局部重试与熔断策略。"""
        correct_cfg = self.harness_config.get("correct", {}) or {}
        max_retries = int(correct_cfg.get("max_retries", 3))
        logger.info("[Correct] retries=%s/%s error=%s", retries, max_retries, error_msg)
        if retries >= max_retries:
            on_failure = correct_cfg.get("on_failure", "ask_human")
            logger.error("[Correct] circuit-breaker on_failure=%s", on_failure)
            return {
                "status": "failed",
                "action": on_failure,
                "error": error_msg,
                "feedback": f"Max retries ({max_retries}) reached. Strategy: {on_failure}. Original error: {error_msg}",
            }
        return {
            "status": "retry",
            "feedback": f"Previous execution failed with: {error_msg}. Please fix your parameters and retry.",
        }

    # ------------------------------------------------------------------
    # KV Cache 对齐上下文
    # ------------------------------------------------------------------

    def build_context(self) -> list[dict[str, Any]]:
        """公开 API：返回 KV Cache 四段 + [Memory] mount 段 messages（SRS FR-MEM-1）。"""
        tools_openai_schema = None
        if self.tool_registry is not None:
            try:
                tools_openai_schema = self.tool_registry.to_openai_schema()
            except Exception:
                tools_openai_schema = None
        return build_kv_aligned_context(
            system_prompt=str(self.model_config.get("system_prompt", "")),
            tools_schema_text=self.tools_config.get("tools_schema"),
            tools_openai_schema=tools_openai_schema,
            trajectory=self.trajectory,
            step_count=self.step_count,
            status_bar_config=self.context_config.get("status_bar", {}) or {},
            terminated=self.is_terminated,
            mounted_layers=list(self._mounted_layers) or None,
        )

    # ------------------------------------------------------------------
    # scoped_worker 上下文隔离管理器（SRS §4.3 FR-MAGT-1 Invariant #3）
    # 语义：
    #   - 进入：snapshot 当前 trajectory / step_count
    #   - 内部：worker 可自由写入 trajectory / step_count（worker 私有）
    #   - 退出（正常或异常）：自动 GC 恢复 snapshot，父级 trajectory 永远不可见 worker 内部中间步骤
    # ------------------------------------------------------------------

    @contextlib.asynccontextmanager
    async def scoped_worker(
        self,
        worker_name: str,
        *,
        inherit_trajectory: bool = True,
    ) -> AsyncIterator[BaseHarnessV2]:
        """`async with harness.scoped_worker("w1") as w:` 得到 worker 子上下文，
        作用域退出后 w 内部 trajectory 自动截断回收，父级不泄漏（SRS FR-MAGT-1 + Invariant #3）。

        参数：
          inherit_trajectory=True（默认）：worker 启动前可看到父级当前 trajectory（只读）；
          inherit_trajectory=False：worker trajectory 从空列表启动（严格隔离）。
        """
        if inherit_trajectory:
            child_trajectory: list[dict[str, Any]] = list(self.trajectory)
            child_step_count: int = int(self.step_count)
            child_terminated: bool = bool(self.is_terminated)
        else:
            child_trajectory = []
            child_step_count = 0
            child_terminated = False
        # (a) 创建浅绑定 worker（同实例，但将 trajectory / step_count / is_terminated 指向局部作用域变量，
        #     退出作用域时恢复父级）。
        # 为实现简洁、不引入额外 copy，使用「栈式恢复」：
        parent_trajectory_ref = self.trajectory
        parent_step_count_ref = self.step_count
        parent_terminated_ref = self.is_terminated
        exc_info: tuple[Any, Any, Any] | None = None
        try:
            self.trajectory = child_trajectory
            self.step_count = child_step_count
            self.is_terminated = child_terminated
            logger.debug(
                "[scoped_worker:%s] ENTER trajectory.len=%s step_count=%s inherit=%s",
                worker_name,
                len(self.trajectory),
                self.step_count,
                inherit_trajectory,
            )
            yield self
        except Exception as _exc:
            import sys as _sys

            exc_info = _sys.exc_info()
            raise
        finally:
            # (b) 退出（正常/异常）：
            #   - CRITICAL（硬约束）：必须用 `del list[n:]` **本体截断** child_trajectory，
            #     而不是重新赋值新列表 —— 外部对 child_trajectory 本体的持有引用也会看到截断结果；
            #   - inherit_trajectory=True 时，前 parent_len 条 dict 是父级 trajectory 的引用，
            #     绝不允许修改这些 dict（历史 bug：清空 content 会污染父级 trajectory 字典）；
            #   - 内容回收仅对**截断出来的切片副本**做置空（不影响 parent）；
            #   - 最后显式 gc.collect() 双保险，防止 worker 大 LLM 响应字符串长生命。
            truncated_slices: list[dict[str, Any]] = []
            try:
                parent_len = len(parent_trajectory_ref) if inherit_trajectory else 0
                if len(child_trajectory) > parent_len:
                    # 保留截断出来的 worker 内部消息，便于我们后续 None-ize 内容（不碰 parent 对象）
                    truncated_slices = list(child_trajectory[parent_len:])
                    # ------------------------------------------------------------------
                    # SRS §4.3 FR-MAGT-1 Invariant #3 硬约束：必须使用 `del list[parent_len:]`
                    # 本体截断，而不是 child_trajectory = child_trajectory[:parent_len]
                    # 后者只改局部变量，外部引用不会观察到截断，内存泄漏 + 上下文泄漏。
                    # ------------------------------------------------------------------
                    del child_trajectory[parent_len:]
                # 仅对 worker 内部的截断切片内容置空加速 GC（绝不修改 parent_len 之前的对象）
                for m in truncated_slices:
                    if not isinstance(m, dict):
                        continue
                    if isinstance(m.get("content"), str):
                        m["content"] = ""
                    if isinstance(m.get("thought"), str):
                        m["thought"] = ""
                    # tool_calls 数组可能是大 JSON，显式清空
                    tcs = m.get("tool_calls")
                    if isinstance(tcs, list):
                        tcs.clear()
            except Exception:
                logger.debug(
                    "[scoped_worker:%s] child truncation non-fatal", worker_name, exc_info=True
                )
            finally:
                truncated_slices.clear()
            self.trajectory = parent_trajectory_ref
            self.step_count = parent_step_count_ref
            self.is_terminated = parent_terminated_ref
            logger.debug(
                "[scoped_worker:%s] EXIT  parent trajectory.len=%s step_count=%s (worker output: GC discarded)",
                worker_name,
                len(self.trajectory),
                self.step_count,
            )
            # 双保险 GC：scoped_worker 退出边界固定点回收 worker 私有轨迹内存与循环引用
            try:
                gc.collect()
            except Exception:  # pragma: no cover - gc.collect() 极少抛
                logger.debug("[scoped_worker:%s] gc.collect non-fatal", worker_name, exc_info=True)
            # 若上层捕获/吞异常，依然保留原始异常语义（不丢 traceback）
            del exc_info

    # ------------------------------------------------------------------
    # 内部：ReAct Loop / Step (Fix Issue #1)
    # ------------------------------------------------------------------

    async def _react_loop(self, initial_user_input: str) -> dict[str, Any]:
        retries_this_turn = 0
        while (
            not self.is_terminated
            and len((self._trace and self._trace.turns) or []) < self.max_turns
        ):
            self.step_count += 1
            step_result = await self._react_step()
            st = step_result.get("status")
            if st == "success" and step_result.get("final_answer") is not None:
                return step_result
            if st == "blocked":
                # Constrain 阻断：直接上报，不再 raise（与 V2 run() 中 blocked 分支契约对齐）
                return step_result
            if st == "failed":
                # Correct 熔断：同样直接上报，避免外层断言被迫匹配 max_turns
                return step_result
            if st == "human_required":
                return step_result
            if st == "retry":
                retries_this_turn += 1
                continue
            retries_this_turn = 0
        return {"status": "failed", "error": f"ReAct exceeded max_turns={self.max_turns}"}

    async def _react_step(self) -> dict[str, Any]:
        assert self._trace is not None, "run() or step() must init trace before _react_step"
        turn = ReActTurnV2(index=len(self._trace.turns))
        self._trace.turns.append(turn)
        retries_this_step = 0
        max_local_retries = max(
            0, int(self.harness_config.get("correct", {}).get("max_retries", 3))
        )
        last_correction: dict[str, Any] | None = None
        # SRS NFR-OBS-1：如果调用方 install_harness_tracer 设置了 otel_tracer，则每轮生成 span `agentlisp.react.turn`
        otel_tracer = getattr(self, "otel_tracer", None)
        turn_attrs: dict[str, Any] | None = None
        span_ctx: Any = None
        if otel_tracer is not None:
            try:
                from .otel_tracer import AGENTLISP_TURN_SPAN
            except Exception:
                AGENTLISP_TURN_SPAN = "agentlisp.react.turn"
            turn_attrs = {
                "agentlisp.run_id": str(self._trace.run_id),
                "agentlisp.agent_name": str(self.agent_name or ""),
                "agentlisp.turn_index": int(turn.index),
            }
            span_ctx = otel_tracer.start_as_current_span(
                AGENTLISP_TURN_SPAN, attributes=dict(turn_attrs)
            )
        try:
            if span_ctx is not None:
                _span_obj = span_ctx.__enter__()
            try:
                self.status_bar.on_step(self._trace.run_id, turn.index, "start")

                while True:
                    # 1) 组装 KV 对齐上下文（每轮 retry 都要重建，因为 correct 的 feedback 会追加进 trajectory）
                    messages = self.build_context()

                    # 2) LLM 决策：CR-16 P1-5 Provider / CircuitBreaker / Context-Leakage 层
                    try:
                        if self._llm_orchestrator is not None:
                            # 走新 orchestrator（primary 过 CircuitBreaker / forbidden_context_keys 过滤 / fallback-model）
                            llm_out = await self._llm_orchestrator.achat(messages)
                        else:
                            llm_out = await self.llm_client.achat(messages)
                    except Exception as exc:  # Provider 层异常统一落 trace：
                        from .llm_client import (
                            ERR_CONTEXT_LEAKAGE,
                            CircuitBroken,
                            HarnessError,
                            ProviderHTTPError,
                        )

                        err_str = str(exc)
                        if isinstance(exc, HarnessError) and ERR_CONTEXT_LEAKAGE in err_str:
                            # FR-CHECK-3 runtime 层 context leakage：trace.status=blocked
                            turn.status = "blocked"
                            self.trajectory.append(
                                {
                                    "role": "assistant",
                                    "content": err_str,
                                    "blocked": True,
                                    "context_leakage": True,
                                }
                            )
                            self.status_bar.on_step(
                                self._trace.run_id, turn.index, "blocked", err_str
                            )
                            await self._save_checkpoint()
                            return {"status": "blocked", "reason": err_str}
                        if isinstance(exc, CircuitBroken):
                            # FR-CORRECT-2：circuit breaker 熔断；strategy ∈ {abort / ask-human / fallback-model}
                            # abort / fallback-model（fallback 也失败）→ trace.status=failed；ask-human → 留给上层 HITL
                            if exc.strategy == "ask-human":
                                turn.status = "blocked"
                                self.trajectory.append(
                                    {
                                        "role": "assistant",
                                        "content": err_str,
                                        "circuit_break": True,
                                        "ask_human_required": True,
                                    }
                                )
                                return {"status": "human_required", "reason": err_str}
                            turn.status = "failed"
                            self.trajectory.append(
                                {"role": "assistant", "content": err_str, "circuit_break": True}
                            )
                            return {"status": "failed", "error": err_str, "feedback": err_str}
                        if isinstance(exc, (ProviderHTTPError, TimeoutError, asyncio.TimeoutError)):
                            # provider 单轮失败（没到 breaker 阈值）：计入 retry
                            last_correction = {
                                "status": "retry",
                                "feedback": (
                                    f"[Provider error] {type(exc).__name__}: {exc}; "
                                    "请重发 tool_call 重试。"
                                ),
                            }
                            self.trajectory.append(
                                {"role": "assistant", "content": last_correction["feedback"]}
                            )
                            retries_this_step += 1
                            if retries_this_step > max_local_retries + 3:
                                # 防御性上限：局部 max_retries 之外再容忍 provider 层面若干次失败
                                turn.status = "failed"
                                return {
                                    "status": "failed",
                                    "error": err_str,
                                    "feedback": err_str,
                                }
                            continue
                        raise  # 其余异常交给 finally 外层 catch
                    assistant_msg = dict(llm_out)
                    content = assistant_msg.get("content")
                    tool_calls = assistant_msg.get("tool_calls")

                    # 无 tool_calls：要么是 final answer，要么是 retry feedback（追加到 trajectory 再跑）
                    if not tool_calls:
                        answer = str(content) if content is not None else ""
                        if last_correction is not None and retries_this_step <= max_local_retries:
                            # 第一次 tool_call verify 失败后 correct 反馈 → 模型回复 content 的情况：
                            # 把 feedback 塞给用户让模型重出 tool_calls（此处把它写回 trajectory 触发下一次模型生成 tool_call）
                            self.trajectory.append({"role": "assistant", "content": answer})
                            retries_this_step += 1
                            if retries_this_step > max_local_retries:
                                turn.answer = answer
                                turn.status = "retry-ignored"
                                return last_correction
                            continue
                        turn.thought = answer or None
                        turn.answer = answer
                        turn.status = "success"
                        self.trajectory.append({"role": "assistant", "content": answer})
                        self.status_bar.on_step(self._trace.run_id, turn.index, "answer", answer)
                        await self._save_checkpoint()
                        return {"status": "success", "final_answer": answer}

                    tc = tool_calls[0]
                    fn = tc["function"]
                    tool_name = fn["name"]
                    action_input: dict[str, Any] = fn.get("arguments") or {}
                    tool_call = {"tool_name": tool_name, "args": action_input}

                    turn.action = tool_name
                    turn.action_input = action_input
                    if not turn.thought and content:
                        turn.thought = str(content)

                    # 3) Constrain → Execute → Verify → Correct 循环
                    allowed, reason = self.constrain(tool_call)
                    if not allowed:
                        turn.status = "blocked"
                        self.trajectory.append(
                            {"role": "tool", "name": tool_name, "content": reason, "blocked": True}
                        )
                        self.status_bar.on_step(self._trace.run_id, turn.index, "blocked", reason)
                        await self._save_checkpoint()
                        return {"status": "blocked", "reason": reason}

                    self.status_bar.on_step(self._trace.run_id, turn.index, "tool_call", tool_call)
                    observation: dict[str, Any]
                    if self.tool_registry is not None and tool_name in (
                        self.tool_registry.names() or []
                    ):
                        try:
                            result = await self.tool_registry.acall(tool_name, **action_input)
                        except Exception as exc:
                            observation = {
                                "exit_code": 1,
                                "stdout": "",
                                "stderr": f"{type(exc).__name__}: {exc}",
                            }
                        else:
                            if isinstance(result, dict) and "exit_code" in result:
                                # 工具本身返回结构化 {exit_code, stdout, stderr}: 直接采用（支持 verify 的 exit_code 断言）
                                observation = {
                                    "exit_code": int(result.get("exit_code", 0)),
                                    "stdout": result.get("stdout", ""),
                                    "stderr": result.get("stderr", ""),
                                }
                            else:
                                observation = {
                                    "exit_code": 0,
                                    "stdout": str(result)
                                    if not isinstance(result, (dict, list))
                                    else result,
                                    "stderr": "",
                                }
                    else:
                        observation = {
                            "exit_code": 0,
                            "stdout": f"[tool {tool_name} not registered; arguments={action_input!r}]",
                            "stderr": "",
                        }

                    passed, verify_msg = self.verify(observation)
                    if not passed:
                        turn.status = "retry"
                        retries_this_step += 1
                        correction = await self.correct(
                            tool_call, verify_msg, retries=retries_this_step
                        )
                        last_correction = correction
                        if correction.get("status") == "failed":
                            turn.status = "failed"
                            self.trajectory.append(
                                {
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": verify_msg,
                                    "verify_failed": True,
                                }
                            )
                            feedback = correction.get("feedback") or correction.get("error") or ""
                            action_info = correction.get("action")
                            # 把熔断策略（fail_fast / ask_human 等）拼进 feedback，run() 读 failed 分支的 error 字段能读到更完整信息
                            if action_info:
                                feedback = (
                                    f"[HarnessCorrect circuit-breaker] strategy={action_info}; "
                                    f"retries_exceeded={retries_this_step}; last_error={feedback or verify_msg}"
                                )
                            self.trajectory.append({"role": "assistant", "content": feedback})
                            correction = dict(correction)
                            correction["feedback"] = feedback
                            correction["error"] = feedback
                            await self._save_checkpoint()
                            return correction
                        # retry：把 verify 失败原因 + correct feedback 追加进 trajectory 继续下一轮
                        self.trajectory.append(
                            {
                                "role": "tool",
                                "name": tool_name,
                                "content": verify_msg,
                                "retry": True,
                            }
                        )
                        self.trajectory.append(
                            {"role": "user", "content": correction.get("feedback") or ""}
                        )
                        await self._save_checkpoint()
                        if retries_this_step > max_local_retries:
                            return last_correction or correction
                        continue

                    # 成功分支
                    turn.observation = observation
                    turn.status = "success"
                    stdout_for_traj = (
                        observation
                        if isinstance(observation, (dict, list))
                        else observation.get("stdout")
                    )
                    self.trajectory.append(
                        {"role": "tool", "name": tool_name, "content": stdout_for_traj}
                    )
                    self.status_bar.on_step(
                        self._trace.run_id, turn.index, "tool_result", observation
                    )
                    await self._save_checkpoint()
                    return {
                        "status": "success",
                        "output": observation.get("stdout", ""),
                        "observation": observation,
                    }
            finally:
                pass
        except asyncio.CancelledError:
            if span_ctx is not None and _span_obj is not None:
                try:
                    _span_obj.record_exception(asyncio.CancelledError())
                except Exception:
                    pass
            raise
        except Exception as exc:
            if self._trace is not None and self.checkpoint_store is not None:
                try:
                    await self.checkpoint_store.save(
                        self._trace.run_id,
                        {
                            "trace": self._trace.to_dict(),
                            "trajectory": list(self.trajectory),
                            "step_count": self.step_count,
                            "is_terminated": self.is_terminated,
                        },
                    )
                except Exception:
                    logger.exception("[Checkpoint] emergency save failed, non-fatal")
            turn.status = "failed"
            if span_ctx is not None and _span_obj is not None:
                try:
                    _span_obj.set_attribute("agentlisp.turn_status", "failed")
                    _span_obj.record_exception(exc)
                except Exception:
                    pass
            raise
        finally:
            try:
                if span_ctx is not None and _span_obj is not None:
                    try:
                        _span_obj.set_attribute("agentlisp.turn_status", str(turn.status or ""))
                    except Exception:
                        pass
                if span_ctx is not None:
                    span_ctx.__exit__(None, None, None)
            except Exception:
                logger.debug("[otel] span end non-fatal error", exc_info=True)
            turn.finished_at = time.monotonic()

    # ------------------------------------------------------------------
    # Checkpoint Hook (Fix Issue #5)
    # ------------------------------------------------------------------

    async def _save_checkpoint(self) -> None:
        if self._trace is None or self.checkpoint_store is None:
            return
        try:
            await self.checkpoint_store.save(
                self._trace.run_id,
                {
                    "trace": self._trace.to_dict(),
                    "trajectory": list(self.trajectory),
                    "step_count": self.step_count,
                    "is_terminated": self.is_terminated,
                },
            )
        except Exception:
            logger.exception("[Checkpoint] save failed, non-fatal, continue")

    async def from_checkpoint(self, run_id: str) -> ExecutionTraceV2:
        payload = await self.checkpoint_store.load(run_id)
        if not payload:
            raise KeyError(f"checkpoint not found: {run_id}")
        # 恢复内存状态
        self.trajectory = list(payload.get("trajectory", []))
        self.step_count = int(payload.get("step_count", 0))
        self.is_terminated = bool(payload.get("is_terminated", False))
        td = payload["trace"]
        self._trace = ExecutionTraceV2(
            run_id=td["run_id"],
            agent_name=td.get("agent_name"),
            started_at=datetime.fromisoformat(td["started_at"]),
            finished_at=datetime.fromisoformat(td["finished_at"])
            if td.get("finished_at")
            else None,
            turns=[
                ReActTurnV2(
                    **{
                        k: v
                        for k, v in t.items()
                        if k
                        in (
                            "index",
                            "thought",
                            "action",
                            "action_input",
                            "observation",
                            "answer",
                            "status",
                            "started_at",
                            "finished_at",
                        )
                    }
                )
                for t in td.get("turns", [])
            ],
            final_answer=td.get("final_answer"),
            status=td.get("status", "pending"),
            error=td.get("error"),
        )
        return self._trace


# ==============================================================================
# 单文件本地冒烟（对应用户提供版本的 __main__ 入口）
# ==============================================================================


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
    print("=== 测试 AgentLisp BaseHarnessV2 合并版运行时 ===")

    harness = BaseHarnessV2(
        model_config={
            "system_prompt": "你是一个自动修复 Bug 的 Agent。",
            "agent_name": "document-repairer-v2",
        },
        context_config={"status_bar": {"step_count": True}},
        tools_config={"tools_schema": "Tool: bash(command: str)"},
        harness_config={
            "constrain": {"forbidden_commands": ["rm -rf"]},
            "correct": {"max_retries": 3, "on_failure": "ask_human"},
        },
    )

    trace = asyncio.run(harness.run("请检查当前目录下的文件"))
    print(
        f"✅ BaseHarnessV2 运行成功：run_id={trace.run_id} status={trace.status} turns={len(trace.turns)} duration_ms={trace.duration_ms}"
    )
    for t in trace.turns:
        print(
            f"   turn[{t.index}] status={t.status} action={t.action!r} duration_ms={t.duration_ms}"
        )
