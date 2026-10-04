# language: zh-CN
功能: AgentLisp v2.0 云原生 Temporal 长流程、人在回路与沙箱防护 (NFR-SEC & IF-TEMPORAL)
  作为 宿主胶水与安全隔离层
  需要提供 Temporal 长流程持久化挂起、人在回路审批与物理沙箱路径越权防护

  背景:
    假如 宿主系统已集成 Temporal Workflow SDK
    并且 配置了双重沙箱锁 (PurePosix + Symlink Path.resolve)

  @NFR-SEC-1a @Workspace-Root-Path-Lock
  场景大纲: workspace_root 路径逃逸与符号链接穿透双重防护
    假如 工作区根目录指定为 "/workspace/sandbox"
    当 工具尝试访问路径 "<target_path>"
    那么 路径安全校验器的判定结果应当为 "<verdict>"

    例子:
      | target_path                             | verdict | 说明                             |
      | /workspace/sandbox/src/main.py          | PASS    | 工作区内正常路径通过             |
      | /etc/passwd                             | BLOCK   | 绝对路径逃逸绝不通过             |
      | /workspace/sandbox/../../etc/shadow     | BLOCK   | 相对路径 .. 穿透拦截             |
      | /workspace/sandbox/symlink_to_outside   | BLOCK   | 符号链接 (Symlink) 物理指向外锁死 |

  @IF-TEMPORAL-1 @Temporal-HITL-Approval
  场景: 敏感工具触发 Temporal 人在回路 (HITL) 挂起与 Signal 唤醒
    假如 工具 "git-push" 被标记为 ":require-approval"
    当 Agent 触发调用 "git-push"
    那么 Temporal Workflow 应当调用 wait_condition 挂起当前栈帧落盘
    并且 状态机状态变更为 "AWAITING_HUMAN_APPROVAL"
    当 运维人员通过 Temporal UI/API 发送 "approve" Signal
    那么 Workflow 恢复栈帧执行并将 git-push 推送到远端
