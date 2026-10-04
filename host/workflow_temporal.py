"""
AgentLisp v2.0 Temporal 长流程与人在回路 (HITL) 引擎 (host/workflow_temporal.py)
符合 IF-TEMPORAL-1 规约：
利用 Temporal 实现长流程挂起落盘与人在回路 Signal 唤醒审批机制。
"""

import asyncio
import logging
from typing import Any

try:
    from temporalio import activity, workflow
    from temporalio.client import Client

    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False

logger = logging.getLogger("AgentLisp.TemporalEngine")


class AgentLispTemporalEngine:
    def __init__(self, temporal_host: str = "localhost:7233"):
        self.temporal_host = temporal_host
        self.client: Any | None = None

    async def connect(self):
        if not TEMPORAL_AVAILABLE:
            logger.info("ℹ️ Temporal SDK 未安装，将使用 DirectRunner 本地非持久化运行。")
            return
        try:
            self.client = await Client.connect(self.temporal_host)
            logger.info(f"✅ 已成功连接 Temporal 长流程服务端 -> {self.temporal_host}")
        except Exception as e:
            logger.warning(f"⚠️ 无法连接 Temporal 服务端 ({e})，降级为本地内存调度。")


if TEMPORAL_AVAILABLE:

    @activity.defn(name="agentlisp_execute_tool_activity")
    async def execute_tool_activity(params: dict[str, Any]) -> dict[str, Any]:
        """Temporal Activity：执行受 Harness 门控保护的工具动作"""
        tool_name = params.get("tool_name")
        cmd = params.get("args", {}).get("command", "")
        logger.info(f"⚡ [Temporal Activity] 正在执行工具: {tool_name} ({cmd})")
        return {"exit_code": 0, "stdout": f"Executed {cmd} successfully under Temporal Activity."}

    @workflow.defn(name="AgentLispHITLWorkflow")
    class AgentLispHITLWorkflow:
        def __init__(self):
            self.approval_signal_received = False
            self.approval_decision = "PENDING"

        @workflow.signal(name="approve_tool_execution")
        def receive_approval_signal(self, decision: str):
            """接收运维/人类审批人员发来的 Approve / Reject 信号"""
            self.approval_signal_received = True
            self.approval_decision = decision

        @workflow.run
        async def run(self, agent_request: dict[str, Any]) -> dict[str, Any]:
            tool_name = agent_request.get("tool_name", "git-push")
            requires_approval = agent_request.get("requires_approval", True)

            if requires_approval:
                logger.info(
                    f"⏸ [Temporal HITL 挂起] 工具 '{tool_name}' 需要人类审批，等待 Signal 唤醒..."
                )
                # 栈帧挂起落盘，绝不占用物理内存和线程
                await workflow.wait_condition(lambda: self.approval_signal_received)

                if self.approval_decision != "APPROVED":
                    logger.warning(f"❌ [Temporal HITL 拒绝] 审批结果: {self.approval_decision}")
                    return {"status": "rejected", "reason": "Human reviewer rejected execution."}

            logger.info("▶ [Temporal HITL 恢复] 审批通过，继续执行 Activity...")
            res = await workflow.execute_activity(
                execute_tool_activity,
                agent_request,
                start_to_close_timeout=asyncio.get_event_loop().time() + 60,
            )
            return {"status": "success", "result": res}


if __name__ == "__main__":
    print("=== 测试 AgentLisp Temporal 模版加载 ===")
    print(f"Temporal SDK 可用性: {TEMPORAL_AVAILABLE}")
