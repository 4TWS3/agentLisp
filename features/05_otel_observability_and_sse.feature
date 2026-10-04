# language: zh-CN
功能: OpenTelemetry 分布式链路追踪与 FastAPI SSE 实时流 (NFR-OBS-1 & IF-API-1)
  作为 运维与可观测性网关
  必须导出符合 OTLP 规范的分布式 Trace Span，并通过 SSE 协议向前端推送实时 Reasoning 轨迹

  背景:
    假如 运行时连接到了 Jaeger OTLP 4317 采集器
    并且 FastAPI 已经挂载了 AgentLisp 网关路由

  @NFR-OBS-1 @OpenTelemetry-Tracing
  场景: ReAct 轮次与 Harness 拦截事件导出为 OpenTelemetry Trace Span
    当 Agent 执行一轮 ReAct 推理与工具调用
    那么 OpenTelemetry Tracer 应当生成操作名为 "agentlisp.react.turn" 的 Span
    并且 Span 属性中应包含 "agent.name", "turn_index", "tool_name", "harness.verdict" 标签
    并且 将 Span 异步发送至 Jaeger (localhost:4317)

  @IF-API-1 @FastAPI-SSE-Streaming
  场景: 通过 Server-Sent Events (SSE) 实时流式推送推理轨迹
    当 客户端发起 HTTP GET 请求 `/v1/agents/repair_agent/stream`
    那么 服务器响应 Header Content-Type 应为 "text/event-stream"
    并且 数据流中应实时推送 "event: reasoning", "event: tool_call", "event: status_bar" 数据包
