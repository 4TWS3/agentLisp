# language: zh-CN
功能: AgentLisp v2.0 上下文、记忆与词法作用域隔离 (FR-MEM & FR-MAGT)
  作为 上下文治理引擎
  需要保障 Static Prefix Cache 高命中率、MarkdownFS 渐进加载以及 Worker 作用域的彻底 GC 隔离

  背景:
    假如 已经初始化 BaseAgentHarnessV2 上下文构建器
    并且 挂载了 MarkdownFS 记忆模块

  @NFR-PERF-1a @Context-KV-Alignment
  场景: 上下文物理组装严格按照 KV Cache 前缀优化布局
    当 调用 build_kv_aligned_context() 组装上下文消息列表
    那么 第一条消息应当为静态 System Prompt
    并且 第二条消息应当为静态 Tool Definitions
    并且 消息末尾固定追加包含当前 Step 数的 <agent_status> StatusBar 挂钩

  @FR-MEM-1 @MarkdownFS-Lazy-Loading
  场景大纲: MarkdownFS 三层记忆 (L0/L1/L2) 渐进式加载
    假如 记忆库根目录下存在 SOUL.md 与 MEMORY.md
    当 请求记载记忆层级为 "<layer>"
    那么 展开注入 Context 的内容应当为 "<content_type>"

    例子:
      | layer | content_type                           |
      | L0    | SOUL.md 全量灵魂约束 + MEMORY.md L0 Abstract 摘要 |
      | L1    | L0 内容 + MEMORY.md L1 Section Overview 概览    |
      | L2    | L1 内容 + 基于 URI/超链接按需惰性调取全文          |

  @FR-MAGT-1 @Scoped-Worker-GC
  场景: scoped-worker 局部 Trajectory 作用域隔离与 GC 原地清理
    假如 主 Agent 创建并进入了子 Agent "code_repair_worker" 作用域
    并且 子 Worker 内部执行了包含 2048 字节日志的调试命令 "pytest -v"
    当 scoped-worker 上下文管理器 (`with scoped_worker(...)`) 运行结束退出
    那么 子 Worker 的局部消息轨迹应被 Python 原地截断清空 (child_trajectory.clear)
    并且 主 Agent 的 build_context() 中绝对不包含子 Worker 的 2048 字节中间日志
    并且 主 Agent 仅接收到 Worker 显式提交的结构化产物 Artifact
