# AgentLisp v2.0 软件需求规格说明书 (SRS)

> 文档代号：`agentlisp_srs` · 版本：`2.0.0` · 基线日期：`2026-10-03`
> 标准：**ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering**
> 上级文档：[agentlisp_specification.md](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_specification.md)（语言设计规范，非验收级）
> 验收原则：**每条需求必须可验证（可量化 / 可复现 / 可判定 PASS/FAIL）**，不可验证项必须返工到「可写出测试代码」的形状。

---

## 1 引言与愿景 (Introduction & Vision)

### 1.1 编写目的
本文档把 AgentLisp v2 的「语言设计规范」转化为工程可验收的**需求规格**：
- 为 `compiler/parser · checker · emitter` 提供验收级错误码；
- 为 `runtime/base_harness_v2.py` 提供 Harness 三重管道 + 5 条 Language Primitives 的可验证执行顺序；
- 为 `host/gateway · workflow · sandbox` 四件套提供接口与协议级字段契约；
- 为 CI `compiler-tests / python-quality / docker-build` job 提供 pass/fail 数字阈值。

### 1.2 适用范围
**Scope-In**：Racket 编译前端、Python Harness 运行引擎、云原生胶水层（FastAPI/Temporal/Docker/E2B/OTel）、examples/*.al 编译样例、.github/workflows/ci.yml。
**Scope-Out**：LLM 自身推理质量、云厂商 PaaS 部署运维手册、第三方 MCP Server 的内部实现。

### 1.3 核心抽象公式

**Agent = Model + Harness**（同时提供 LaTeX 版本供文档工具渲染）：
$$
\text{Agent} = \text{Model} + \text{Harness}
$$

> 说明：Model（LLM 推理层）≠ Agent。Agent 的「可预测行为」完全由 Harness 的静态声明（编译期）+ 运行时管道（runtime）决定。凡是不经过 Harness 三重管道的调用都属于**架构违规**，应在编译期或运行时被拒绝。

### 1.4 术语表 (Glossary)

| 术语 | 定义 |
|---|---|
| DSL (AgentLisp) | 以 S-表达式书写的 Agent 声明式语言，文件后缀 `.al` |
| Harness | Agent 的行为外壳，固定为 Constrain → Execute → Verify → Correct 四重管道 |
| KV Cache | LLM Provider 提供的 Prompt 前缀缓存；本 SRS 要求静态段在前、动态段在后，形成稳定四层前缀 |
| MCP | Model Context Protocol，Agent 调用外部工具/服务的标准协议（stdio/HTTP/SSE 三类 transport）|
| HITL (Human In The Loop) | 人在回路，通过 Temporal Signal（APPROVE/REJECT）或 FastAPI `/v1/runs/{run_id}/approve` 中断/恢复长流程 |
| DCAF L0/L1/L2 | 文档型记忆分层：L0 原子事实 / L1 概念概述 / L2 完整文本，三层在 runtime 中分别惰性加载 |
| scoped-worker | 多 Agent 拓扑下的「词法作用域子 Agent」，退出作用域后局部轨迹自动 GC（不可见父级 build_context）|
| τ²-bench | AgentLisp 官方代码修复端到端基准测试集（详见 §6.3）|
| Traceability | 29148 可追溯性：每条需求必须可反查「测试用例 ID + 代码文件:行号」 |

---

## 2 总体描述与架构分层 (Overall Description)

### 2.1 四层编译架构（严格单向依赖）

```
自然语言意图 / 业务用户故事
    ↓ (人工 / Agent)
① AgentLisp .al DSL 源文件  (S-expression / EBNF 语法)
    ↓ parse
② AgentLisp AST            (5 块：Static/Dynamic/Harness 必选 + MultiAgent 可选)
    ↓ check (编译期三条 ERR_ 失败即 exit 1)
③ Python BaseHarnessV2 子类代码  (HARNESS_REGISTRY[name] = XxxHarness)
    ↓ run (运行时三重管道)
④ Host 宿主层挂接：FastAPI(SSE) / Temporal(gRPC) / E2B(Docker) / Jaeger(OTLP 4317)
```

### 2.2 运行环境限制
- Python：>= 3.12.0（CPython）；
- Racket：>= 8.10；
- Docker Engine：>= 24.0 + Compose v2（`include:` 语法要求 >= 2.20）；
- Redis：7-alpine（infra 已钉镜像）；
- Temporal：auto-setup:1.24.0（infra 已钉镜像，DB=sqlite）；
- Jaeger：jaegertracing/all-in-one:latest（infra 已钉镜像，OTLP gRPC 4317）。

### 2.3 关注点分离原则 (Separation of Concerns)
- `.al` 源文件**只允许**声明认知逻辑 + 护栏；**禁止**写 HTTP 路由、Temporal Workflow、Docker 启动命令等宿主职责；
- 编译期 checker 只做**静态可判定**的检查（类型 / 范围 / 值域 / 顺序 / 作用域），禁止访问外部网络、禁止调用 LLM；
- runtime 层可选依赖（FastAPI/Temporal/docker-py/mcp/anthropic/openai/otel）**全部采用 FeatureNotInstalledError** 模式，import 永远不崩，真实调用时才给出 `uv pip install 'agentlisp[GROUP]'` 安装命令。

---

## 3 功能性需求 (Functional Requirements)

> 验收准则：每条 FR-* 必须在 CI 中有 ≥1 个对应 pytest / RackUnit 用例，且用例元数据 `@pytest.mark.req("FR-CHECK-1")` 绑定。

| 需求 ID | 标题 | 可验证通过条件（29148 MUST） | 现有代码映射（可追溯锚） |
|---|---|---|---|
| **FR-PARSER-1** | 语法解析 + EBNF AST | 对任意符合 §3 EBNF 的合法 `.al`，`parse-defagent` 返回的 AST 必须含有 5 个必选块 + 可选 MultiAgent 块；非法 S-exp 必须抛出结构化 `exn:agentlisp:parse`，**禁止**出现 Racket 原生 `match: no matching clause` 崩溃 | [agentlisp_compiler.rkt: parse-defagent L83-L121](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L83-L121) |
| **FR-PARSER-2** | Provider 枚举校验 + Temperature 范围 | provider ∈ {`anthropic`, `openai`, `qwen`, `mock`}（字符串）；temperature ∈ `[0.0, 1.0]`（实数），否则 FR-PARSER-2 FAIL | [parse-model L125-L145](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L125-L145) |
| **FR-PARSER-3** | Memory Policy KV 对齐 | `:auto-append`（spec 命名，**禁止**使用旧命名 `:auto-append-episodic`）必须透传到 `context_config.auto_append_episodic`（Python 下划线键）；DSL 中任意 `#t/#f` 值均不会静默丢失 | [parse-memory-policy L165-L175](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L165-L175) + emit context 段 |
| **FR-PARSER-4** | Tools 四种组合必全支持 | 以下 4 种都必须 parse 成功，不得崩溃：① 仅 `define-tool` × N；② 仅 `import-builtin`；③ 仅 `import-mcp URL`；④ 任意组合 | [parse-tools L180-L216](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L180-L216) |
| **FR-PARSER-5** | Correct on-failure 值域 | on-failure ∈ {`ask-human`, `fallback-model`, `abort`} 三枚举，其他值一律 FR-PARSER-5 FAIL | [CORRECT-ON-FAILURE-ENUM L77-L79](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L77-L79) + [parse-correct L258-L271](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L258-L271) |
| **FR-PARSER-6** | MultiAgent topology 枚举 + scoped-worker 最小解析 | topology ∈ {`peer`, `orchestration`, `decentralised`, `judge-driven`}；每个 scoped-worker 必须至少含 `name + model + tools + harness` 四块 | [parse-multi / parse-scoped-worker L272-L305](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L272-L305) |
| **FR-CHECK-1** | **ERR_KV_ALIGNMENT_VIOLATION**（KV 对齐违规）| 静态块（`:model` / `:tools`）任一块出现在动态块（`:context`）之后 → checker 必须抛出标准错误码 `ERR_KV_ALIGNMENT_VIOLATION` 且 exit 1；合法顺序不抛 | [check-kv-alignment-order L337-L351](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L337-L351) |
| **FR-CHECK-2** | **ERR_UNGUARDED_TOOL_EXECUTION**（裸工具防护）| 当使用有副作用 builtin = {`bash`, `git-push`} 时，以下两条件**至少满足一个**：(a) `verify` 断言非空（json_schema/linter_check/test_runner/reviewer_agent 任一为真或有值）；(b) `constrain.require_approval ∩ tool_name ≠ ∅` 或 `constrain.forbidden_commands` 明确声明该工具。任一违反 → 抛出 `ERR_UNGUARDED_TOOL_EXECUTION` 且 exit 1 | [check-unguarded-tool-execution L356-L377](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L356-L377) |
| **FR-CHECK-3** | **ERR_CONTEXT_LEAKAGE**（编译期词法隔离）| scoped-worker 内部 `define-tool` 的 tool_name 集合 ∩ 父级 `define-tool` 的 tool_name 集合 ≠ ∅ → 抛出 `ERR_CONTEXT_LEAKAGE` 且 exit 1；空交集合法 | [check-context-leakage L379-L395](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L379-L395) |
| **FR-RUN-1** | Harness 四重管道固定序 | 任何 tool_call 必须严格按以下序推进：`Constrain → Execute → Verify → (Correct loop if fail) → Append Trajectory / Return Final`；顺序错乱在单测里可被 StatusBar 回调事件顺序断言为 FAIL | [runtime/base_harness_v2.py: _react_step L520-L640](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L520-L640) |
| **FR-RUN-2** | Constrain 精确匹配（禁止子串误杀）| Constrain 默认采用 token_boundary 匹配 = shlex token 级比对 + 正则词边界 `\b` fallback。**反例必须 PASS（不拦截）**：forbidden=`rm`，cmd=`mkdir /tmp/remove_logs` / `ls category` / `echo git reset --hard 的用法`；**正例必须 FAIL（拦截）**：forbidden=`rm -rf`，cmd=`rm -rf /`；forbidden=`cat`，cmd=`cat /etc/passwd` | [emit-constrain-method L650-L685](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L650-L685) + [runtime/_contains_forbidden_token](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L455-L490) |
| **FR-RUN-3** | Constrain workspace-root 路径门控（NFR-SEC 配合）| 若 `harness_config.constrain.workspace_root` 不为 None，则任何 tool_call.args.command 中出现的绝对路径或 `../` 必须经过 `pathlib.is_relative_to(workspace_root)` 校验；违规拦截，错误信息含 `WorkspaceEscape` | （代码位置：runtime/base_harness_v2.py `constrain` 方法，待落地到本轮迭代之后）|
| **FR-RUN-4** | Verify 失败驱动 Correct 熔断 | 构造如下场景：LLM 无限返回 exit_code=1 的 bash 命令；设 `correct.max_retries=2`，必须在第 2 次重试后进入 circuit-breaker，trace.status=failed 且 trace.error 含 `strategy=<on_failure>`，而不是被全局 max_turns 截断 | [runtime/tests/test_harness_v2.py: test_verify_failure_triggers_correct_then_circuit_breaker](file:///Users/lee/products/agentLisp/runtime/tests/test_harness_v2.py#L191-L233) |
| **FR-MEM-1** | Markdown L0/L1/L2 渐进式加载 | Harness 构造时，若 context_config.markdown_fs 非空，则 emitter 必须生成 mount 代码：`self.memory_fs = MarkdownFS(path).mount('L0-Abstract',lazy=True) / L1 / L2`；build_context 的 system prompt 前缀应含 `[Memory] mounted layers: L0-Abstract, L1-Overview, L2-FullText` 一行字符串 | （emitter 生成 mount 代码，待落地）+ [runtime/memory_fs.py: MemoryFS + LazyMarkdownLayer](file:///Users/lee/products/agentLisp/runtime/memory_fs.py#L1-L90) |
| **FR-MAGT-1** | **ERR_CONTEXT_LEAKAGE（运行时版）scoped-worker 轨迹自动 GC** | 提供 Python 上下文管理器 `with scoped_worker(name, model, tools, harness):`：进入时 fork trajectory 子视图；离开时 discard；`h.build_context()` 在外层作用域返回的 messages **完全不可包含** worker 内部 turn 的 stdout / tool_name；可写 pytest 形如：worker 内调用 `bash pwd`，父 build_context 搜索字符串 `pwd`/`stdout from bash` 断言不存在 | （runtime 待落地 scoped_worker 上下文管理器）|

---

## 4 非功能性需求 (Non-Functional Requirements)

> 验收准则：每条 NFR-* 除了代码支持，必须提供 **Measurements（度量方法）+ Threshold（阈值）+ Pass/Fail 判定** 三要素。29148 严格禁止「只写定性语句」。

| 需求 ID | 领域 | 阈值 (Threshold) | 度量方法 (Measurements) | 代码/CI 映射 |
|---|---|---|---|---|
| **NFR-PERF-1a** | Prompt Prefix Cache 命中率 | **≥ 85%** | 对 `examples/production-repair-agent.al` 连续跑 100 轮不同 repair task（仅 user_input 变化）；计算 `len(prompt_static_bytes) / len(prompt_total_bytes)` 的均值 ≥ 0.85 视为 PASS。prompt_static_bytes 定义 = build_context 返回的 messages[0] + messages[1]（system prompt + tools_definition 两段）总字符数 | [runtime/base_harness_v2.py: build_kv_aligned_context](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L140-L243) |
| **NFR-PERF-1b** | 首 Token 延迟降低率 | **≥ 50%**（P50 latency 对比 v0.1 baseline 无分层 baseline） | baseline = 用 v0.1 `python/agentlisp_runtime.engine.AgentEngine` 跑同一 100 轮 task，采集首 token P50；v2 同模型同 provider 同温度，采集 P50；(baseline_v0 - v2) / baseline_v0 ≥ 0.5 为 PASS | （CI `perf-*` job 未来补，当前本地测试先跑 MockLLMClient 只做字节占比验证 1a）|
| **NFR-PERF-2** | 编译器 wall-clock 时间（parse + check + emit）| **< 200 ms** | `time racket compiler/main.rkt -i examples/production-repair-agent.al -o /tmp/out.py --check-only` 的 real time 必须 <0.2s（200ms），Ubuntu runner 10 次几何均值 <200ms 为 PASS | （.github/workflows/ci.yml `compiler-tests` job `time ...` 断言 未来补）|
| **NFR-SEC-1a** | Constrain workspace-root 路径锁（配合 FR-RUN-3）| 所有绝对路径 / 包含 `..` 的路径必须在 `workspace_root` 下，否则拦截 PASS | pytest：设 `workspace_root=/app/workspace`，命令 `cat /etc/passwd` → 拦截 FAIL；`cat /app/workspace/a.md` → 通过 | （runtime constrain 待补） |
| **NFR-SEC-1b** | HITL require-human-approval 挂起率 | 凡在 `constrain.require_human_approval` 中的 tool_name，实际执行前**必须**触发一次 human_required 事件（stream_async 可观察到），且在 `TemporalRunner` 下必须用 `Workflow.await Signal("approve")` 挂起；提前执行视为 NFR-SEC-1b FAIL | （host/workflow.py TemporalRunner 未来补） |
| **NFR-SEC-1c** | 沙箱隔离（Docker / E2B）| NullSandbox 跳过；DockerSandbox 提供 `mem_limit / network_mode=none / readonly root fs`；E2BSandbox 提供 `e2b.Sandbox(template=...)`，FeatureNotInstalledError 才允许抛 | [host/sandbox.py: NullSandbox + DockerSandbox](file:///Users/lee/products/agentLisp/host/sandbox.py#L1-L130)（E2B 类未来补）|
| **NFR-REL-1** | Redis Checkpoint TTL | 默认 **≥ 86400 s**（24h）| 验收方法：pytest fixture 启动 Redis 7-alpine container，构造 `RedisCheckpointStore(url, key_prefix='agentlisp:test:')` 不指定 ttl → 调用 `save(run_id, trace)` → `redis-cli TTL key` 返回 ≥ 86390 秒（容忍 10s 执行误差）为 PASS | [runtime/checkpoint.py: RedisCheckpointStore L45-L95](file:///Users/lee/products/agentLisp/runtime/checkpoint.py#L45-L95)（默认值 86400 需钉死） |
| **NFR-OBS-1** | ReAct 轮次 OTel Span 注入 | `_react_step()` 每轮 turn 必须包在 `tracer.start_as_current_span("agentlisp.react.turn", attributes={agent_name, turn_index, status})` 内；Span export 到 OTLP gRPC 4317（Jaeger）；若没装 otel 组则 FeatureNotInstalledError | （runtime/otel_tracer.py 未来补）+ [infra/docker-compose.infra.yml jaeger 4317](file:///Users/lee/products/agentLisp/infra/docker-compose.infra.yml#L56-L72) |
| **NFR-REL-2** | ExecutionTrace 证据链完整性（THS 三维判定素材）| 每次 `BaseHarnessV2.run()` 返回的 trace 必须非空包含：run_id UUID / agent_name / status ∈ {pending,success,failed,human_required} / started_at 与 finished_at（ISO8601）/ turns[i].duration_ms ≥0 / final_answer 或 error 二选一。缺失任一字段视为 FAIL | [runtime/base_harness_v2.py: ExecutionTraceV2 + ReActTurnV2 @dataclass](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L40-L95) |

---

## 5 外部接口需求 (External Interface Requirements)

### 5.1 IF-CLI-1 编译器 CLI 字段级规格

| 长选项 | 短选项 | 参数 | 必填 | 说明 |
|---|---|---|---|---|
| `--input` | `-i` | `FILE.al` | ✅ | 输入 AgentLisp 源文件 |
| `--output` | `-o` | `FILE.py` | 条件：`--check-only` 未设置 | 输出 Python BaseHarnessV2 子类模块路径 |
| `--check-only` | 无 | 无 | 否 | 仅 parse + check，不 emit Python；成功 exit 0，失败 exit 1 或 2 |
| `--module-name` | `-m` | 字符串 | 否 | Emit 的 Python 顶层 module 名，默认从 output 推导；用于 `python -m <module>` 验证 |
| `--json-errors` | 无 | 无 | 否 | 错误码 + 定位改为 JSON 输出到 stderr，便于 CI 收集 |
| `--version` | `-V` | 无 | 否 | 打印 SRS 版本号 + 编译器版本并 exit 0 |

**IF-CLI-1 exit code 编码表**（CI 必须断言）：
| Code | 含义 |
|---|---|
| 0 | 成功（--check-only 全过 / emit 完成）|
| 1 | **编译期检查失败**（= FR-CHECK-1/2/3 触发，标准 ERR_* 错误码）|
| 2 | Parse 失败（= FR-PARSER-* 触发，结构化 parse error）|
| 3 | IO 失败（文件不存在 / 无写权限 / 编码错误）|
| >=4 | 保留（编译器内部 panic 或未分类异常）|

### 5.2 IF-SDK-1 BaseAgentHarness Python SDK 必签名

```python
class BaseHarnessV2(Protocol):
    agent_name: str
    tool_registry: Any
    checkpoint_store: Any
    memory_fs: Any
    status_bar: Any
    trace: ExecutionTraceV2

    def __init__(
        self,
        model_config: Dict[str, Any],
        context_config: Dict[str, Any],
        tools_config: Dict[str, Any],
        harness_config: Dict[str, Any],
        agent_name: Optional[str] = None,
        llm_client: Optional[Any] = None,
        tool_registry: Optional[Any] = None,
        checkpoint_store: Optional[Any] = None,
        memory_fs: Optional[Any] = None,
        status_bar: Optional[Any] = None,
        max_turns: int = 30,
        react_mode: bool = True,
    ) -> None: ...
    def build_context(self, trajectory: Optional[List[Dict]] = None) -> List[Dict]: ...
    def constrain(self, tool_call: Dict) -> Tuple[bool, str]: ...
    def verify(self, observation: Dict) -> Tuple[bool, str]: ...
    async def correct(self, tool_call: Dict, error_msg: str, retries: int) -> Dict: ...
    def step(self, user_input: Optional[str] = None) -> Awaitable[Dict]: ...
    def run(self, user_input: str = "", timeout_ms: int = 3_600_000) -> ExecutionTraceV2: ...
    def run_async(self, user_input: str = "", timeout_ms: int = 3_600_000) -> Awaitable[ExecutionTraceV2]: ...
    def stream_async(self, user_input: str = "", timeout_ms: int = 3_600_000) -> AsyncIterator[Dict]: ...
```

### 5.3 IF-API-1 FastAPI 流式 (SSE) 契约

| Method | Path | 输入（JSON）| 输出 | 关键行为 |
|---|---|---|---|---|
| GET | `/health` | 无 | `{"status":"ok","version":"2.0.0","checkpoint":true/false,"otel":true/false}` | FeatureNotInstalledError 不能让 GET /health 崩；status_bar on_start 可触发 |
| POST | `/v1/agents/{name}/run` | `{"input":"…", "stream": true, "timeout_ms": 3600000, "workflow": null}` | stream=true → SSE 事件：`event:start` / `event:turn` / `event:human_required` / `event:done` / `event:error`；stream=false → JSON ExecutionTrace | stream=true 必须设置 `Cache-Control: no-cache`、`Connection: keep-alive`、`Content-Type: text/event-stream` |
| GET | `/v1/runs/{run_id}` | 无 | `{"run_id":"…","status":"…","final_answer":…,"turn_count":N}` | Redis 不存在抛 404 |
| POST | `/v1/runs/{run_id}/approve` | `{"approved": true, "comment": "…"}` | 202 Accepted | 对应 TemporalRunner `approve` Signal；未挂起返回 409 Conflict |

### 5.4 IF-TEMPORAL-1 Temporal gRPC Signal 契约

- 连接端点：`TEMPORAL_ADDR` env，默认 `temporal:7233`（infra 已钉）；
- Workflow 名称：`AgentLispRunWorkflow`；
- 必需 Signals：`approve(comment: str)` / `reject(comment: str)`；
- 必需 Queries：`status()`、`current_turn_index()`、`trace_head(n=10)`。

### 5.5 IF-MCP-1 MCP 协议接入 scheme 白名单

`parse-tools` 的 `import-mcp URL` 必须匹配 scheme ∈ {`stdio://`，`http+unix://`，`https://`，`sse://`}，任何其它 scheme 直接 FR-PARSER-FAIL（parse 阶段拒绝）。

---

## 6 验收与测试标准 (Acceptance Criteria)

### 6.1 AC-1 编译期断言测试集（RackUnit + `compiler/tests/`）

> 判定表：每条 ERR_ 至少 4 组反例 + 至少 2 组合法正例。总数 ≥ 3 × 6 = 18 个 RackUnit cases。

| ID（可追溯） | 绑定需求 | 反例（应该 exit 1）| 正例（应该 exit 0）|
|---|---|---|---|
| AC-1-KV-1 | FR-CHECK-1 | :context 写在 :model 之后 | :model → :tools → :context（标准序）|
| AC-1-KV-2 | FR-CHECK-1 | :context 写在 :tools 之后 | 空 tools 集合（仅 builtin） |
| AC-1-KV-3 | FR-CHECK-1 | :context 写在中间，:model 与 :tools 一个在前后 | 两个子 defagent 文件 merge 正确序 |
| AC-1-KV-4 | FR-CHECK-1 | scoped-worker 内部块顺序错（不应该泄漏父级，但至少 parse 出 worker 错块序） | scoped-worker 顺序对 |
| AC-1-UN-1 | FR-CHECK-2 | 用 bash builtin，verify 全空，没 require_approval/forbidden | 用 bash builtin，verify.test_runner="pytest tests/" |
| AC-1-UN-2 | FR-CHECK-2 | git-push 声明了，require_approval 写的是别的工具名 | require_approval 含 `git-push` |
| AC-1-UN-3 | FR-CHECK-2 | forbidden 是空串（误杀所有命令，parse 阶段应提前失败） | forbidden 非空（`rm -rf`）+ verify json_schema #t（双保险）|
| AC-1-UN-4 | FR-CHECK-2 | 组合副作用：bash + git-push 全有，guard 全空 | 单个工具 + guard ok |
| AC-1-CL-1 | FR-CHECK-3 | 父级 define-tool `write-md`，子 worker 内部也 define-tool `write-md` 同名字 | 子 worker 命名 `write-md-*worker-only*` 不重名 |
| AC-1-CL-2 | FR-CHECK-3 | 3 个 scoped-worker + 父级，工具名重名 | 1 个 scoped-worker 正常不重名 |
| AC-1-CL-3 | FR-CHECK-3 | 子工具名是父工具名的前缀字符串但非重名（AC 应该 PASS，测试反误杀） | 名字合法，也必须 PASS 正例 |
| AC-1-CL-4 | FR-CHECK-3 | 跨多个 multi-agent topology peer 对 peer 工具重名 | judge-driven 下法官工具 与 参与者工具 不重名 |
| + 6 个 parser 正/反例 | FR-PARSER-1/2/3/4/5/6 | 温度 2.0 / provider = "abc" / on-failure=ask_human（下划线非法）/ memory :auto-append 丢值 / tools 只 builtin 或只 mcp / topology=`foo-bar`（7 条 FR-PARSER FAIL） | 合法 7 条 PASS |

### 6.2 AC-2 运行时 Harness 拦截测试集（pytest `runtime/tests/`）

> 规模：当前 13 用例；本轮迭代目标 ≥ 24 用例。新增缺口绑定如下：

| ID（SRS 新增）| 绑定需求 | 断言要点 |
|---|---|---|
| AC-2-FR-RUN-3 | FR-RUN-3 + NFR-SEC-1a | workspace_root=/app，命令 `cat /etc/passwd` → 拦截，reason 含 WorkspaceEscape |
| AC-2-FR-MEM-1 | FR-MEM-1 | emitter 产物 import 后，`self.memory_fs` 非空；build_context system 前缀含 `[Memory] mounted layers: L0-Abstract, L1-Overview, L2-FullText` |
| AC-2-FR-MAGT-1 | FR-MAGT-1（运行时 context leakage）| worker 内执行 bash pwd；父 build_context 里不出现 `pwd`/`bash pwd` / stdout 字符串 |
| AC-2-NFR-REL-1 | NFR-REL-1 | Redis TTL ≥ 86390s |
| AC-2-NFR-PERF-1a | NFR-PERF-1a | 静态段字节占比 ≥ 85%（production-repair-agent + 100 轮不同 user_input，MockLLMClient）|
| AC-2-NFR-OBS-1 | NFR-OBS-1 | 用 in-memory otel exporter，确认 agentlisp.react.turn span 数量 = turn_count |
| AC-2-NFR-SEC-1b | NFR-SEC-1b | require_approval 工具触发 human_required event，stream_async 可捕获；且在 step 前不调用 tool |
| 其余至 24：边界值 / 错误注入（max_turns=0 / 网络异常 / 工具不存在）| 其它 FR/NFR | pytest 边界值矩阵 |

### 6.3 AC-3 τ²-bench 端到端代码修复率 ≥ 90%

> 29148 可验证四要素（必须具备否则本条直接判定 FAIL 且不允许灰度）：

| 要素 | 具体规格 |
|---|---|
| **数据集 DOI / Tag** | τ²-bench v1.0，GitHub Release `agentlisp/t2-bench@v1.0`（标签 `τ²-bench-v1.0`）。数据集包含 1000 个真实开源 Python/JS/TS 项目 bug，每个 bug = (初始代码 commit + failing pytest 输出 + 期望修复后的 pytest 全绿 commit 哈希) |
| **修复率公式** | `fix_rate = (# {sample_i | τ²_pass(sample_i) == True}) / 1000` |
| **τ²_pass(sample) 的成功判定（三条件 AND）**| (1) Agent 生成的 `git diff` 应用到代码后**无 SyntaxError / ImportError**（`python -m compileall` / `tsc --noEmit`）；(2) `pytest tests/` 对该 bug 的失败用例全部通过（不得用 `--deselect`/跳过/xfail）；(3) `reviewer-agent`（若启用）打分 ≥ 0.8（[0,1] 连续分，人工评审 10% 采样校准） |
| **运行命令** | `agentlisp-bench run --dataset t2-bench/v1.0 --timeout 600s --sample-range 1..1000 --max-turns 30 --report json > report.json`；报告需包含 `fix_rate_total` 字段 + `sample_id` 级 `detail[]` 数组 |
| **通过阈值** | `fix_rate_total ≥ 0.90`（**≥ 900 / 1000** samples 成功）为 AC-3 PASS |

---

## 附录 A ISO/IEC/IEEE 29148 Traceability 返工清单（SRS 原版本 5 条强制项，已在本文档补全）

> 对应本 SRS 早期摘要版的 5 条不合格项（Rev R 1..5）；本版本已全部修补并写入正文章节锚，允许 Cx 项目进入下一阶段。

| 返工编号 | 原问题 | 本文档修复锚 |
|---|---|---|
| R1 | FR-CHECK-3 与 FR-MAGT-1 验收边界错位（编译期 / 运行时混写） | §3 拆成 FR-CHECK-3（编译期 tool 重名）+ FR-MAGT-1（运行时 trajectory GC），两条各自有 pass/fail 判定 |
| R2 | NFR-PERF-1 ≥85% / ↓50% 缺度量方法 | §4 NFR-PERF-1a/1b 独立两条，分别给出 prompt 字节占比 + latency 对比 的度量方法 + 阈值 |
| R3 | IF-CLI-1 缺字段级规格表 + exit code | §5.1 完整表（长/短选项、exit code 6 档编码）|
| R4 | NFR-REL-1 TTL 86400 验收方法未写（24h 不可测）| §4 NFR-REL-1 改为 pytest Redis container + `redis-cli TTL ≥ 86390`（容忍 10s），CI 可直接跑 |
| R5 | AC-3 τ²-bench ≥90% 不可验证（无数据集 / 公式 / 判定 / 命令）| §6.3 补 4 要素 + 数据集 tag + 运行命令 + 阈值，29148 合规 |

---

## 附录 B 需求 ↔ 测试 ↔ 代码 可追溯性矩阵（初版骨架，随迭代补全）

| 需求 ID | pytest / RackUnit 用例 ID | 代码锚（初版） |
|---|---|---|
| FR-PARSER-1~6 | test_parser_* / compiler/tests/test-core.rkt (待扩展) | compiler/agentlisp_compiler.rkt parse 段 |
| FR-CHECK-1 | test_err_kv_alignment_violation (RackUnit ×4) | check-kv-alignment-order L337 |
| FR-CHECK-2 | test_err_unguarded_tool_execution (RackUnit ×4) | check-unguarded-tool L356 |
| FR-CHECK-3 | test_err_context_leakage (RackUnit ×4) | check-context-leakage L379 |
| FR-RUN-1 | test_harness_pipeline_event_order | _react_step L520-L640 |
| FR-RUN-2 | test_constrain_token_boundary[pytest parametrize ×7] | runtime base_harness_v2 constrain |
| FR-RUN-3 | (新增 AC-2-FR-RUN-3) | runtime constrain 未来 patch 点 |
| FR-RUN-4 | test_verify_failure_triggers_correct_then_circuit_breaker | test_harness_v2.py L191 |
| FR-MEM-1 | (新增 AC-2-FR-MEM-1) | emitter 生成 mount（待实现） |
| FR-MAGT-1 | (新增 AC-2-FR-MAGT-1) | scoped_worker cm（待实现） |
| NFR-PERF-1a | (新增 AC-2-NFR-PERF-1a) | build_kv_aligned_context |
| NFR-PERF-2 | CI compiler-tests job `time ... < 0.2s` | compiler/main.rkt CLI |
| NFR-SEC-1a/1b/1c | AC-2 新增 3 cases | constrain + TemporalRunner + Sandbox |
| NFR-REL-1 | AC-2-NFR-REL-1 | RedisCheckpointStore default TTL=86400 |
| NFR-OBS-1 | AC-2-NFR-OBS-1 | runtime/otel_tracer.py（待实现）|
| IF-API-1 (3 routes) | host gateway route smoke tests | host/gateway.py |
| AC-3 τ²-bench ≥90% | `agentlisp-bench run` report.json fix_rate_total 断言 | future `scripts/bench/` |
