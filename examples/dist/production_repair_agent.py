# -*- coding: utf-8 -*-
"""
Step C 辅助产物：模拟 production-repair-agent.al 的 emitter 输出（预期形状）
用于：
  (1) Python ast.parse 语法校验（无连字符类名、Status Bar 角色为 system、constrain 精确匹配）
  (2) BaseHarnessV2 构造 + MockLLMClient 2 轮 roundtrip
  (3) SRS §6 AC-1/AC-2 的 "真实生产级 Harness 继承类" 验收锚
（本文件是手动模拟的「正确形状预期产物」；真实 emitter 应生成等价结构。
  待 CI racket 编译后可与本文件逐字段 diff 对齐）
"""
from __future__ import annotations

import json
from runtime.base_harness_v2 import BaseHarnessV2, build_kv_aligned_context

AGENT_NAME = "production-repair-agent"

AGENT_MODEL_CONFIG = {
    "provider": "anthropic",
    "name": "claude-3-5-sonnet-20241022",
    "temperature": 0.2,
    "system_prompt": (
        "你是一名精通 Python / TypeScript / Rust 的代码修复 Agent（topology=judge-driven，on-failure=fallback-model → ask-human）。\n"
        "角色与责任（固化到静态段）：\n"
        "  - 你只处理代码修复，不回答自然语言闲聊；最终输出必须是 patch + pytest passing log。\n"
        "  - 你继承 scoped-worker 的隔离语义：父子/兄弟 worker 间 define-tools 名永不重名（ERR_CONTEXT_LEAKAGE 已在编译期拦截）。\n"
        "  - 你输出的 tool_calls 必须同时过双护栏：verify 非空 OR require_approval 且 non-empty forbidden。\n"
        "静态工作流程（按顺序执行，不得跳步）：\n"
        "  (1) 读取 failing pytest 输出（Trajectory 第 1 条 observation，禁止跳过）\n"
        "  (2) 在 workspace_root=/app 内定位出错源码文件（read-file / grep-builtin，限制相对路径）\n"
        "  (3) 通过 linter-check 先过语法与 import 检查（再失败时 correct 触发 max_retries=3）\n"
        "  (4) 生成 patch（write-md / apply-patch-builtin），然后重新跑 test-runner = pytest tests/（不允许 --deselect）\n"
        "  (5) 若连续 2 次 pytest 未全绿：自动触发 reviewer-agent = \"judge\"（拓扑 judge-driven 规范）\n"
        "  (6) 最终返回 FINAL_ANSWER = 修复后的 diff + pytest 全绿日志摘要 + τ²-bench 样本 meta\n"
        "护栏常量（禁止修改）：\n"
        "  - correct.on_failure ∈ {ask-human, fallback-model, abort}；require_approval={deploy_prod, git_push_main}\n"
        "  - forbidden=[\"rm -rf /\", \"DROP TABLE\", \"password\", \"secret\"]；workspace_root=/app（相对路径逃逸会被 Constrain 拦截）\n"
        "评价标准（静态段）：成功样本 = compileall/tsc 通过 ∧ failing 用例全过 ∧ reviewer-agent ≥ 0.8；目标 fix_rate ≥ 0.90（τ²-bench 1000）。\n"
    ),
    "agent_name": AGENT_NAME,
}

AGENT_TOOLS_SCHEMA_TEXT = (
    "<tools_definition>\n"
    "[Builtins] read-file(path: str) -> {ok: bool, content: str, exit_code: int}\n"
    "[Builtins] bash(command: str, timeout_ms: int = 120000) -> {exit_code: int, stdout: str, stderr: str}\n"
    "[Builtins] git-push(remote: str, branch: str) -> {exit_code: int, stdout: str, stderr: str}  (require_approval)\n"
    "[Builtins] apply-patch-builtin(patch: str, cwd: str) -> {exit_code: int, stdout: str, stderr: str}\n"
    "[Builtins] grep-builtin(pattern: str, path: str) -> {matches: [{file: str, line: int, content: str}], exit_code: int}\n"
    "[MCP] mcp_vscode_lsp (stdio://./tools/mcp_vscode_lsp.py) → did_open, did_change, execute_command(\"ruff.check\", args=[])\n"
    "[MCP] mcp-reviewer (http+unix:///run/user/1000/mcp-reviewer.sock) → review_fix(patch, tests_log) → score: 0.0..1.0\n"
    "[Custom Tools]\n"
    "  - write-md(path: str, content: str) -> {ok: bool, saved_bytes: int, sha256: str}\n"
    "  - test-runner(cwd: str, pytest_args: List[str]) -> {exit_code: int, summary: str, failed: List[str]}\n"
    "  - linter-check(cwd: str, paths: List[str]) -> {exit_code: int, diagnostics: List[{file, line, msg}]}\n"
    "  - deploy_prod(env: str, version: str) -> {status: str}  (require_approval)\n"
    "</tools_definition>\n"
)

AGENT_CONTEXT_CONFIG = {
    "markdown_fs": "./docs/memory",
    "layers": ["L0-Abstract", "L1-Overview", "L2-FullText"],
    "auto_append_episodic": True,
    "skills": ["python-debugging", "typescript-linting", "rust-cargo-fmt", "dacf-ths-criteria"],
    "status_bar": {
        "step_count": True,
        "current_branch": True,
        "test_status": True,
        "time_tracker": True,
        "todo_list": True,
        "custom": {
            "workspace_root": "/app",
            "dataset_tag": "τ²-bench-v1.0",
            "fix_rate_target": "0.90",
        },
    },
    "compression": "rolling-summary-window-20",
}

AGENT_TOOLS_CONFIG = {
    "tools_schema": AGENT_TOOLS_SCHEMA_TEXT,
    "import_builtins": ["read-file", "bash", "git-push", "apply-patch-builtin", "grep-builtin"],
    "mcp_servers": [
        "stdio://./tools/mcp_vscode_lsp.py",
        "http+unix://%2Frun%2Fuser%2F1000%2Fmcp-reviewer.sock/",
    ],
    "define_tools": [
        {"name": "write-md",
         "input": [("path", "string"), ("content", "string")],
         "output": [("ok", "boolean?"), ("saved_bytes", "number?")]},
    ],
}

AGENT_HARNESS_CONFIG = {
    "constrain": {
        "require_approval": ["write-md", "git-push", "apply-patch-builtin"],
        "forbidden_commands": ["rm -rf", "git reset --hard", "shutdown -h now",
                               "curl | bash", "wget | sh", "chmod -R 777"],
        "workspace_root": "/app",
        "_matching": "token_boundary",
    },
    "verify": {
        "json_schema": True,
        "linter_check": True,
        "test_runner": "pytest tests/ --maxfail=1 -q",
        "reviewer_agent": "judge",
    },
    "correct": {"max_retries": 3, "circuit_breaker": 5, "on_failure": "ask-human"},
}


class ProductionRepairAgentHarness(BaseHarnessV2):
    """SRS §6 production-repair-agent：生产级代码修复 Harness（emitter 目标形状）。"""

    agent_name = AGENT_NAME

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("agent_name", AGENT_NAME)
        kwargs.setdefault("model_config", AGENT_MODEL_CONFIG)
        kwargs.setdefault("context_config", AGENT_CONTEXT_CONFIG)
        kwargs.setdefault("tools_config", AGENT_TOOLS_CONFIG)
        kwargs.setdefault("harness_config", AGENT_HARNESS_CONFIG)
        super().__init__(*args, **kwargs)

    # ---------------- emitter 生成的 build_context KV 四段挂钩 -----------------
    def build_context(self, trajectory=None):
        trajectory = trajectory if trajectory is not None else self.trajectory
        # 把 tools_openai_schema 作为静态段 1 拼好（这里为 roundtrip 简化，直接空 schema 列表）
        tools_openai_schema: list = []
        return build_kv_aligned_context(
            system_prompt=self.model_config["system_prompt"],
            tools_schema_text=AGENT_TOOLS_SCHEMA_TEXT,
            tools_openai_schema=tools_openai_schema,
            trajectory=trajectory,
            step_count=self.step_count,
            status_bar_config=self.context_config.get("status_bar", {}),
            terminated=self.status_bar._terminated if hasattr(self.status_bar, "_terminated") else False,
        )


HARNESS_REGISTRY = {AGENT_NAME: ProductionRepairAgentHarness}

__all__ = [
    "AGENT_NAME",
    "AGENT_MODEL_CONFIG",
    "AGENT_CONTEXT_CONFIG",
    "AGENT_TOOLS_CONFIG",
    "AGENT_HARNESS_CONFIG",
    "ProductionRepairAgentHarness",
    "HARNESS_REGISTRY",
]


if __name__ == "__main__":
    import asyncio
    h = ProductionRepairAgentHarness()
    trace = asyncio.run(h.run("请修复 failing pytest 的 traceback。"))
    out = {
        "module": "production_repair_agent",
        "agents": [AGENT_NAME],
        "trace": {
            "run_id": str(trace.run_id),
            "status": trace.status,
            "turn_count": len(trace.turns),
            "final_answer": trace.final_answer,
            "error": trace.error,
        },
        "harness_registry_keys": list(HARNESS_REGISTRY.keys()),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
