# language: zh-CN
功能: AgentLisp v2.0 Harness 运行时控制流管道 (FR-RUN)
  作为 Agent 运行时引擎
  必须强制执行 Constrain -> Verify -> Correct 三重防护管道
  以确保所有的工具调用在确定的安全边界与闭环断言内运行

  背景:
    假如 已经实例化 BaseAgentHarnessV2 运行时
    并且 挂载了工作区沙箱锁与配置了负面清单规则

  @FR-RUN-1 @Constrain-Negative-List
  场景大纲: Harness Constrain 负面清单精确过滤
    假如 Harness 负面清单配置了规则 "<forbidden_pattern>"
    当 Agent 尝试执行命令 "<input_command>"
    那么 Constrain 门控的拦截结果应当为 "<decision>"

    例子:
      | forbidden_pattern | input_command               | decision | 说明                 |
      | rm -rf            | rm -rf /var/log             | BLOCKED  | 危险删除命令绝对拦截 |
      | rm -rf            | mkdir /tmp/rm_rf_logs       | ALLOWED  | 避免子串匹配误杀     |
      | cat               | cat /etc/shadow             | BLOCKED  | 敏感读取命令精准拦截 |
      | cat               | ls category                 | ALLOWED  | 单词前缀不误杀       |

  @FR-RUN-2 @Verify-Assertion
  场景: Verify 自动化静态/动态断言校验
    假如 工具执行返回了 stdout "SyntaxError: invalid syntax" 且 exit_code 为 1
    当 执行 Harness Verify 门控断言
    那么 Verify 断言判定应当为 "FAILED"
    并且 返回错误上下文 "Linter assertion failed: SyntaxError detected"

  @FR-CORRECT-1 @Correct-Silent-Retry
  场景大纲: Correct 静默重试与 circuit-breaking 熔断
    假如 Verify 断言连续失败次数为 "<retry_count>"
    并且 Harness 配置的最大重试上限 max_retries 为 3
    当 触发 Correct 纠错管道
    那么 运行时采取的动作应当为 "<action>"

    例子:
      | retry_count | action                             |
      | 1           | SILENT_RETRY_WITH_FEEDBACK         |
      | 2           | SILENT_RETRY_WITH_FEEDBACK         |
      | 3           | CIRCUIT_BREAK_TRIGGER_ASK_HUMAN   |

  @FR-RUN-4 @ExecutionTraceV2
  场景: 完整 ReAct 轨迹与离线质溯落盘
    当 Agent 完成一轮 ReAct 推理与工具执行
    那么 系统应当生成包含 uuid, turn_index, thought, tool_call, observation, harness_verdict 的 ExecutionTraceV2 日志
    并且 状态自动同步存入 Redis Checkpoint Store
