"""
AgentLisp v2.0 核心运行时基类 (runtime/base_agent_harness.py)
固化架构规范：
1. KV Cache 严格前缀对齐 (Static System Prompt -> Static Tools -> Trajectory -> Status Bar)
2. Harness 三重控制流管道 (Constrain -> Execute -> Verify -> Correct)
"""

import asyncio
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


class BaseAgentHarness:
    def __init__(
        self,
        model_config: dict[str, Any],
        context_config: dict[str, Any],
        tools_config: dict[str, Any],
        harness_config: dict[str, Any],
    ):
        self.model_config = model_config
        self.context_config = context_config
        self.tools_config = tools_config
        self.harness_config = harness_config

        # 运行时状态
        self.trajectory: list[dict[str, Any]] = []
        self.step_count: int = 0
        self.is_terminated: bool = False

    # ------------------------------------------------------------------
    # 1. KV Cache 对齐的上下文组装器 (Static -> Dynamic -> Trailing Hook)
    # ------------------------------------------------------------------
    def build_context(self) -> list[dict[str, Any]]:
        """
        严格按照 AgentLisp 规约组装 Context：
        [1. System Prompt (Static)] -> [2. Tool Schemas (Static)]
        -> [3. History Trajectory (Dynamic)] -> [4. Status Bar (Trailing Hook)]
        """
        messages = []

        # (1) 静态 System Prompt
        sys_prompt = self.model_config.get("system_prompt", "You are a helpful Agent.")
        messages.append({"role": "system", "content": sys_prompt})

        # (2) 静态工具声明 (有助于 LLM 供应商进行 Prefix Caching)
        if "tools_schema" in self.tools_config:
            messages.append(
                {
                    "role": "system",
                    "content": f"<tools_definition>\n{self.tools_config['tools_schema']}\n</tools_definition>",
                }
            )

        # (3) 动态历史轨迹 (Trajectory)
        messages.extend(self.trajectory)

        # (4) 尾部 Status Bar 挂钩 (防止模型长对话迷失)
        status_items = self.context_config.get("status_bar", {})
        if status_items.get("step_count", True):
            status_bar_str = (
                f"<agent_status>Step: {self.step_count} | Status: Active</agent_status>"
            )
            messages.append({"role": "user", "content": status_bar_str})

        return messages

    # ------------------------------------------------------------------
    # 2. Harness 三重安全与控制流管道
    # ------------------------------------------------------------------
    def constrain(self, tool_call: dict[str, Any]) -> tuple[bool, str]:
        """【护栏 1：约束 (Constrain)】负面清单与工作区安全锁"""
        cmd = tool_call.get("args", {}).get("command", "")
        forbidden_list = self.harness_config.get("constrain", {}).get("forbidden_commands", [])

        for forbidden in forbidden_list:
            if forbidden in cmd:
                logging.warning(f"❌ [Constrain 拦截] 触发禁用命令: {forbidden}")
                return False, f"Harness Blocked: Execution of '{forbidden}' is strictly forbidden."

        return True, "OK"

    def verify(self, observation: dict[str, Any]) -> tuple[bool, str]:
        """【护栏 2：验证 (Verify)】结果静态/动态断言"""
        # 如果观察结果中存在语法/Linter 错误
        if observation.get("exit_code", 0) != 0:
            err_msg = observation.get("stderr", "Execution failed")
            logging.warning(f"⚠️️ [Verify 失败] 输出断言不通过: {err_msg}")
            return False, err_msg

        return True, "Verified"

    async def correct(
        self, tool_call: dict[str, Any], error_msg: str, retries: int
    ) -> dict[str, Any]:
        """【护栏 3：纠正 (Correct)】局部静默重试与降级"""
        max_retries = self.harness_config.get("correct", {}).get("max_retries", 3)
        logging.info(f"🔄 [Correct 自动纠错] 第 {retries}/{max_retries} 次重试...")

        if retries >= max_retries:
            on_failure = self.harness_config.get("correct", {}).get("on_failure", "ask_human")
            logging.error(f"🚨 [Correct 熔断] 已达最大重试上限，触发终态策略: {on_failure}")
            return {"status": "failed", "action": on_failure, "error": error_msg}

        # 内部静默重试逻辑（可返回反馈提示给模型）
        return {
            "status": "retry",
            "feedback": f"Previous execution failed with: {error_msg}. Please fix your parameters.",
        }

    # ------------------------------------------------------------------
    # 3. 核心 ReAct 步骤驱动循环
    # ------------------------------------------------------------------
    async def step(self, user_input: str | None = None) -> dict[str, Any]:
        self.step_count += 1
        if user_input:
            self.trajectory.append({"role": "user", "content": user_input})

        context = self.build_context()
        logging.info(f"🚀 [Step {self.step_count}] 上下文组装完毕，消息数: {len(context)}")

        # 模拟模型决策与工具调用（实际运行时替换为真实的 LLM API 调用）
        mock_tool_call = {"tool_name": "bash", "args": {"command": "ls -la"}}

        # 运行 Harness 管道
        allowed, reason = self.constrain(mock_tool_call)
        if not allowed:
            self.trajectory.append({"role": "tool", "content": reason})
            return {"status": "blocked", "reason": reason}

        # 模拟执行工具
        mock_observation = {"exit_code": 0, "stdout": "file1.py\nfile2.py", "stderr": ""}

        passed, verify_msg = self.verify(mock_observation)
        if not passed:
            correction = await self.correct(mock_tool_call, verify_msg, retries=1)
            return correction

        self.trajectory.append({"role": "tool", "content": mock_observation["stdout"]})
        return {"status": "success", "output": mock_observation["stdout"]}


# ----------------------------------------------------------------------
# 本地验证：单文件可直接运行测试
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=== 测试 AgentLisp BaseAgentHarness 运行时 ===")

    # 初始化配置
    agent_harness = BaseAgentHarness(
        model_config={"system_prompt": "你是一个自动修复 Bug 的 Agent。"},
        context_config={"status_bar": {"step_count": True}},
        tools_config={"tools_schema": "Tool: bash(command: str)"},
        harness_config={
            "constrain": {"forbidden_commands": ["rm -rf"]},
            "correct": {"max_retries": 3, "on_failure": "ask_human"},
        },
    )

    # 运行一步测试
    asyncio.run(agent_harness.step("请检查当前目录下的文件"))
    print("✅ BaseAgentHarness 运行成功！")
