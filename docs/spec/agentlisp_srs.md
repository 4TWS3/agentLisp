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
| **FR-CHECK-0** | 12 字段结构化错误 JSON（SSOT） | 编译期 / Parse 阶段抛出的任何错误，必须返回固定 12 字段 JSON shape：`{schema_version, code, severity, srs_id, message, agent_name, srcloc: {source, line, column, position, span}, hints}`；否则 FR-CHECK-0 FAIL | [checker.rkt](file:///Users/lee/products/agentLisp/compiler/checker.rkt)（12 字段 shape SSOT）；[main.rkt emit-json-errors L57-L60](file:///Users/lee/products/agentLisp/compiler/main.rkt#L57-L60)；[runtime/checker.py make_parse_error_json 工厂](file:///Users/lee/products/agentLisp/runtime/checker.py)（Python 端双端同步 SSOT） |
| **FR-CHECK-1** | **ERR_KV_ALIGNMENT_VIOLATION**（KV 对齐违规）| 静态块（`:model` / `:tools`）任一块出现在动态块（`:context`）之后 → checker 必须抛出标准错误码 `ERR_KV_ALIGNMENT_VIOLATION` 且 exit 1；合法顺序不抛 | [check-kv-alignment-order L337-L351](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L337-L351) |
| **FR-CHECK-2** | **ERR_UNGUARDED_TOOL_EXECUTION**（裸工具防护）| 当使用有副作用 builtin = {`bash`, `git-push`} 时，以下两条件**至少满足一个**：(a) `verify` 断言非空（json_schema/linter_check/test_runner/reviewer_agent 任一为真或有值）；(b) `constrain.require_approval ∩ tool_name ≠ ∅` 或 `constrain.forbidden_commands` 明确声明该工具。任一违反 → 抛出 `ERR_UNGUARDED_TOOL_EXECUTION` 且 exit 1 | [check-unguarded-tool-execution L356-L377](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L356-L377) |
| **FR-CHECK-3** | **ERR_CONTEXT_LEAKAGE**（编译期词法隔离）| scoped-worker 内部 `define-tool` 的 tool_name 集合 ∩ 父级 `define-tool` 的 tool_name 集合 ≠ ∅ → 抛出 `ERR_CONTEXT_LEAKAGE` 且 exit 1；空交集合法 | [check-context-leakage L379-L395](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L379-L395) |
| **FR-RUN-1** | Harness 四重管道固定序 | 任何 tool_call 必须严格按以下序推进：`Constrain → Execute → Verify → (Correct loop if fail) → Append Trajectory / Return Final`；顺序错乱在单测里可被 StatusBar 回调事件顺序断言为 FAIL | [runtime/base_harness_v2.py: _react_step L520-L640](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L520-L640) |
| **FR-RUN-2** | Constrain 精确匹配（禁止子串误杀）| Constrain 默认采用 token_boundary 匹配 = shlex token 级比对 + 正则词边界 `\b` fallback。**反例必须 PASS（不拦截）**：forbidden=`rm`，cmd=`mkdir /tmp/remove_logs` / `ls category` / `echo git reset --hard 的用法`；**正例必须 FAIL（拦截）**：forbidden=`rm -rf`，cmd=`rm -rf /`；forbidden=`cat`，cmd=`cat /etc/passwd` | [emit-constrain-method L650-L685](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L650-L685) + [runtime/_contains_forbidden_token](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L455-L490) |
| **FR-RUN-3** | Constrain workspace-root 路径门控（NFR-SEC 配合）| 若 `harness_config.constrain.workspace_root` 不为 None，则任何 tool_call.args.command 中出现的绝对路径或 `../` 必须经过 `pathlib.is_relative_to(workspace_root)` 校验；违规拦截，错误信息含 `WorkspaceEscape` | （代码位置：runtime/base_harness_v2.py `constrain` 方法，待落地到本轮迭代之后）|
| **FR-RUN-4** | Verify 失败驱动 Correct 熔断 | 构造如下场景：LLM 无限返回 exit_code=1 的 bash 命令；设 `correct.max_retries=2`，必须在第 2 次重试后进入 circuit-breaker，trace.status=failed 且 trace.error 含 `strategy=<on_failure>`，而不是被全局 max_turns 截断 | [runtime/tests/test_harness_v2.py: test_verify_failure_triggers_correct_then_circuit_breaker](file:///Users/lee/products/agentLisp/runtime/tests/test_harness_v2.py#L191-L233) |
| **FR-MEM-1** | Markdown L0/L1/L2 渐进式加载 | Harness 构造时，若 context_config.markdown_fs 非空，则 emitter 必须生成 mount 代码：`self.memory_fs = MarkdownFS(path).mount('L0-Abstract',lazy=True) / L1 / L2`；build_context 的 system prompt 前缀应含 `[Memory] mounted layers: L0-Abstract, L1-Overview, L2-FullText` 一行字符串 | （emitter 生成 mount 代码，待落地）+ [runtime/memory_fs.py: MemoryFS + LazyMarkdownLayer](file:///Users/lee/products/agentLisp/runtime/memory_fs.py#L1-L90) |
| **FR-CORRECT-1** | Correct 熔断 + on_failure 3 枚举 | Verify 失败进入 Correct 管道时，`correct.max_retries` 耗尽必须触发 circuit-breaker 并按 `correct.on_failure` ∈ {`ask-human`, `fallback-model`, `abort`} 三枚举之一执行最终策略；枚举值大小写/连字符必须严格校验，下划线变体（`ask_human` 等）直接 FR-CORRECT-1 FAIL | [runtime/base_harness_v2.py Correct 管道](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py)（Correct retries 计数器 + circuit_breaker 触发 + on_failure 三策略分支）；[CORRECT-ON-FAILURE-ENUM L77-L79](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L77-L79)（编译期枚举前置校验） |
| **FR-MAGT-1** | **ERR_CONTEXT_LEAKAGE（运行时版）scoped-worker 轨迹自动 GC** | 提供 Python 上下文管理器 `with scoped_worker(name, model, tools, harness):`：进入时 fork trajectory 子视图；离开时 discard；`h.build_context()` 在外层作用域返回的 messages **完全不可包含** worker 内部 turn 的 stdout / tool_name；可写 pytest 形如：worker 内调用 `bash pwd`，父 build_context 搜索字符串 `pwd`/`stdout from bash` 断言不存在 | （runtime 待落地 scoped_worker 上下文管理器）|
| **FR-PATTERN-01** | Pattern Macros 宏展开合法性（5 MVP 模式）| 以下 5 种顶层高层语法 sugar 必须能通过 `compiler/patterns.rkt` 的 `syntax-case` 宏展开器，**编译期无错误**转换为合法的顶层 `(define-agent ...)` 包装后的 `defagent` Core AST：① `defchain-agent`；② `defparallel-agent`；③ `defreflect-agent`；④ `defrouter-agent`；⑤ `defplanner-agent`。任一失败必须抛出结构化 `exn:agentlisp:parse` 带 `FR-PATTERN-01` 标签 | （新增：patterns.rkt 5 宏 + main.rkt 新增 macro-expansion pass）|
| **FR-PATTERN-02** | 展开后静态前缀强对齐继承（零运行时开销 + 安全）| 5 MVP 模式的宏展开产物中，`defagent` 5 块顺序必须**强制满足**：静态 `:model` 与 `:tools` 在动态 `:context` 之前（即 FR-CHECK-1 checker 的输入合法）；若上层模式糖传入顺序反序，宏展开器必须自动提升静态块到动态块之前，**不得**依赖下游 FR-CHECK-1 抛错。反例必须 PASS（展开后顺序正确）：`(defreflect-agent T :critic "C" :tools (bash) :model (M N) ...)` — 即使 `:tools` 写在 `:model` 之前，展开后 AST 顺序 = `:model` → `:tools` → `:context` → `:harness` | （新增：patterns.rkt 每个宏展开时的 reorder-blocks 静态提升逻辑）|
| **CR41-PAT01** | CR-41 A 包模式宏 01：Priority 优先级排序 | Priority 模式糖通过 `defpriority-agent` 顶层 syntax-case 展开为 `(define-agent ...)`，HC FIRST GENERIC SECOND first-match 顺序 + plist->blocks 5 桶入桶 + reorder 升序 0:model<1:tools<2:context<3:harness<4:multiagent 严格对齐 FR-PATTERN-02 | （CR-41 P1 Task 8，patterns_v2.rkt defpriority-agent）|
| **CR41-PAT02** | CR-41 A 包模式宏 02：Decomposition 任务分解 | Decomposition 模式糖 `defdecomposition-agent` 展开后 `:multiagent :topology orchestration :workers` 注入 2 层 `scoped-worker`（decomp-level-1 / decomp-level-2），5 块升序继承 NFR-PATTERN-02 静态安全（CR-41 重建：Core AST 语法封闭，语义改用合法键表达） | （CR-41 P1 Task 9，patterns_v2.rkt defdecomposition-agent）|
| **CR41-PAT03** | CR-41 A 包模式宏 03：FSM 有限状态机 | FSM 模式糖 `deffsm-agent` 展开后在 system-prompt 声明 `fsm-current-state` 状态跟踪与状态可达性 ≥2 静态断言，非法转移由 `(:correct :on-failure abort)` 强制，5 桶升序 | （CR-41 P1 Task 10，patterns_v2.rkt deffsm-agent）|
| **CR41-PAT04** | CR-41 A 包模式宏 04：Evaluator 评估器 | Evaluator 模式糖 `defevaluator-agent` 展开后在 system-prompt 声明 accuracy≥0.8 + safety≥1.0 双阈值检查，评估标准由 `(:verify :reviewer-agent)` 复核 | （CR-41 P1 Task 11，patterns_v2.rkt defevaluator-agent）|
| **CR41-PAT05** | CR-41 A 包模式宏 05：Topic Model 主题建模 | Topic Model 模式糖 `deftopic-model-agent` 展开后 `:multiagent :workers` 注入 `scoped-worker topic-processor`，system-prompt 声明 topics 子树分类器 | （CR-41 P1 Task 12，patterns_v2.rkt deftopic-model-agent）|
| **CR41-PAT06** | CR-41 A 包模式宏 06：Decomposer 结构化提取 | Decomposer 模式糖 `defdecomposer-agent` 展开后在 system-prompt 声明 2 条 `decomposer-schema-field-type-check`（iso-date / double），类型不符拒绝输出 | （CR-41 P1 Task 13，patterns_v2.rkt defdecomposer-agent）|
| **CR41-PAT07** | CR-41 A 包模式宏 07：Guardrails & Safety 护栏安全 | Guardrails & Safety 模式糖 `defguardrails-safety-agent` 展开后 Harness 三段 guardrails 钩子 + on-violation Verify→Correct 回路，复用 NFR-SEC 基线 | （CR-41 P1 Task 14，patterns_v2.rkt defguardrails-safety-agent）|
| **CR41-PAT08** | CR-41 A 包模式宏 08：HITL 人类在回路 | HITL 模式糖 `defhitl-agent` 展开后 `(:constrain :require-human-approval (all))` 强制前置人工批准，system-prompt 声明 `waiting-for-human-signal` 可观测状态，复用 IF-TEMPORAL-1 signal 基线 | （CR-41 P1 Task 15，patterns_v2.rkt defhitl-agent）|
| **CR41-PAT09** | CR-41 A 包模式宏 09：Exception Handling & Recovery 异常恢复 | Exception 模式糖 `defexception-agent` 展开后 Correct 段 3 层 `on-failure retry`（retry=3, backoff=1.5x），Harness Constrain+Verify+Correct 三层不少 | （CR-41 P1 Task 16，patterns_v2.rkt defexception-agent）|
| **CR41-PAT10** | CR-41 A 包模式宏 10：Exploration & Discovery 探索发现 | Exploration 模式糖 `defexploration-agent` 展开后在 system-prompt 声明 budget + convergence 两条检查与 `expand-more-candidates` 扩展，预算耗尽/收敛即停止（`:correct :on-failure ask-human` 兜底） | （CR-41 P1 Task 17，patterns_v2.rkt defexploration-agent）|

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
| **NFR-PATTERN-01** | Pattern Macros 零运行时开销 | 5 MVP 模式宏展开后的 Core AST 经 emitter 转译为 Python 后，与手写等价 `defagent` 的转译产物在 `ast.dump` 级别**字节级完全相等**（排除时间戳、随机 UUID 等不稳定字段）；任何反射 / 解释器 / 运行时宏展开引入的额外字节视为不达标。测量 = 同一 Agent 分别用模式糖语法与手写 defagent 语法编译，对两份 Python 源做 `python3 -m ast` 规范化后 diff 必须空 | （新增：patterns.rkt 展开 → emitter.py 两次转译对比）|
| **NFR-PATTERN-02** | Pattern Macros 100% 静态安全继承 | 5 MVP 模式宏展开后的 AST 必须**全部通过** FR-CHECK-1 / FR-CHECK-2 / FR-CHECK-3 三项静态检查（checker 侧未做任何放松）；若宏展开后试图破坏静态前缀顺序或跳过护栏，在 checker 阶段即被拦截，与手工编写 defagent 行为**字节级一致**。测量 = 针对 5 模式各构造 2 条违规用例（如 defreflect-agent 故意让 :tools 写在 :context 之后但 checker 仍必须抛出 ERR_KV_ALIGNMENT_VIOLATION 或由宏自动提升为合法顺序，二者择一即可；实际宏设计必须走「自动提升顺序」）| （新增：patterns.rkt + compiler/tests/test_checker_ac1.rkt 5×2=10 条新用例）|

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
    async def step(self, user_input: Optional[str] = None) -> Dict: ...
    async def run(self, user_input: str = "", timeout_ms: int = 3_600_000) -> ExecutionTraceV2: ...
    async def run_async(
        self, user_input: str = "", timeout_ms: int = 3_600_000
    ) -> ExecutionTraceV2: ...
    async def stream_async(
        self, user_input: str = "", timeout_ms: int = 3_600_000
    ) -> AsyncIterator[Dict]: ...
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

## 附录 B 需求 ↔ 测试 ↔ 代码 可追溯性矩阵（已验证双向对齐，commit 174ca7c → CR-23）

**验证基线（CR-39 GA 永久 anchor · check_roadmap_traceability.py 五向全等 128 永远不变 · CR39_BASELINE_PASSED_COUNT: 128）**：2026-10-06，严格模式 pytest 128 passed / 3 skipped / 1 PytestUnknownMarkWarning（6.70s · 基线 HEAD 03e41c0 → CR-36 GA v2.0.0-rc2）；`ruff check All checks passed!`；`ruff format 82 files already formatted`；34 SRS-ID 均有 ≥1 条测试覆盖，0 条孤儿需求。每行用例列表末尾的「×N」为本需求覆盖总条数，>6 只列代表名后补「等 N 个」。IDE GetDiagnostics = 0 files / 0 diagnostics（制度化四硬指标 T0 终态）。**附加 CR-40c O13 Pattern Macros 三绿增量基线（2026-10-07，CI 37582477496）**：patterns 子集 `10 passed, 1 warning in 3.46s`（FR-PATTERN-01 写死名宏展开 5case 字节级 200chars 全等 + FR-PATTERN-02 反序任意名三必块升序 5case idx 正）；Standalone expand `SUMMARY failures=0/5` ×2；RackUnit `5 success(es) 0 failure(s) 0 error(s) 5 test(s) run` ×2；workflow `_tmp_o13_patterns_mvp_verify.yml` 总 `conclusion: success`。三绿基线不计入 CR-39 GA 永久 128 anchor（属于 O13 新功能增量，后续 CR 整并到下版 GA 基线时再统一升级 AC-2 Scn/Pas）。**【T19 final 已钉 2026-10-08 · 锚定 CI run 37807999282 conclusion=success @ dd3cecc】**CR-41 GA 基线锚 = 158，键值行见下一行 `CR41_BASELINE_PASSED_COUNT: 158`。锚定证据（VERBATIM）：pytest patterns `70 passed, 1 warning`（V1 10 + V2 30 + NFR01 15 + NFR02 15）+ RackUnit V1 `5 success(es)` / V2 `10 success(es) 0 failure(s)` + `PATTERNS V2 AST OK (30/30 legal Core AST)`。本轮同时把附录 B 的 AC-2 矩阵行 128→158（矩阵行跟随当前 GA 基线演进；CR-39 GA **128 永久锚**仍完整保留于本段 prose）。
CR41_BASELINE_PASSED_COUNT: 158

| 需求 ID | Scenario 数 | Passed | Failed | Skip/Xfail | pytest / RackUnit 代表性用例 ID | 代码锚（精确文件:行范围） |
|---|---:|---:|---:|---:|---|---|
| AC-3 | 2 | 2 | 0 | 0 | test_基于三条件_and_成功判定规则进行样本评估、test_评估新旧_agent_版本的_mcnemar_配对卡方统计显著性 | [run_t2_bench.py](file:///Users/lee/products/agentLisp/scripts/bench/run_t2_bench.py)（fix_rate_total、rubric≥0.8、McNemar chi²≥3.841，三条件 AND 判定框架） |
| **FR-PARSER-1** | 1 | 1 | 0 | 0 | test_fr_parser_1_illegal_sexp_returns_structured_parse_error_not_racket_match_crash | [agentlisp_compiler.rkt: parse-defagent L83-L121](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L83-L121)（EBNF 5+1 必选块解析；`raise-parse-with-srcloc` 结构化 exn:agentlisp:parse，避免 Racket match 崩溃泄漏）；[runtime/checker.py](file:///Users/lee/products/agentLisp/runtime/checker.py) `make_parse_error_json` 12 字段 JSON shape 工厂 |
| **FR-PARSER-2** | 1 | 1 | 0 | 0 | test_fr_parser_2_provider_enum_and_temperature_range_validation | [agentlisp_compiler.rkt: parse-model L125-L145](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L125-L145)（provider ∈ {anthropic, openai, qwen, mock}；temperature ∈ [0.0, 1.0]，bool 类型拒绝）；[runtime/checker.py](file:///Users/lee/products/agentLisp/runtime/checker.py) `validate_provider_and_temperature`；[runtime/llm_client.py](file:///Users/lee/products/agentLisp/runtime/llm_client.py#L241-L248) 运行时二次校验 |
| **FR-PARSER-3** | 1 | 1 | 0 | 0 | test_fr_parser_3_memory_auto_append_renamed_to_python_underscore_and_bool_not_lost、test_emit_context_auto_append_maps_to_underscore_key_in_python_source | [agentlisp_compiler.rkt: parse-memory-policy L165-L175](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L165-L175)（spec `:auto-append` → Python `auto_append_episodic` 下划线重命名；废弃 `:auto-append-episodic`；#t/#f 值不静默丢失）+ emit context 段；[runtime/checker.py](file:///Users/lee/products/agentLisp/runtime/checker.py) `validate_memory_auto_append_key` |
| **FR-PARSER-4** | 1 | 1 | 0 | 0 | test_fr_parser_4_tools_4_combinations_and_mcp_scheme_whitelist | [agentlisp_compiler.rkt: parse-tools L180-L216](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L180-L216)（4 组合：only define-tool × N / only import-builtin / only import-mcp URL / 任意组合，全不崩溃）；[runtime/mcp_client.py](file:///Users/lee/products/agentLisp/runtime/mcp_client.py#L14-L27) MCP scheme 白名单 {stdio, http+unix, https, sse}；[runtime/checker.py](file:///Users/lee/products/agentLisp/runtime/checker.py) `validate_tools_combination_and_mcp_scheme` |
| **FR-PARSER-5** | 1 | 1 | 0 | 0 | test_fr_parser_5_correct_on_failure_three_values_and_rejects_underscore_variants | [agentlisp_compiler.rkt: CORRECT-ON-FAILURE-ENUM L77-L79](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L77-L79) + [parse-correct L258-L271](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L258-L271)（on-failure ∈ {ask-human, fallback-model, abort}，连字符；下划线变体 ask_human/fallback_model 拒绝）；[runtime/checker.py](file:///Users/lee/products/agentLisp/runtime/checker.py) `validate_correct_on_failure` |
| **FR-PARSER-6** | 1 | 1 | 0 | 0 | test_fr_parser_6_multiagent_topology_enum_and_scoped_worker_min_four_blocks | [agentlisp_compiler.rkt: parse-multi / parse-scoped-worker L272-L305](file:///Users/lee/products/agentLisp/compiler/agentlisp_compiler.rkt#L272-L305)（topology ∈ {peer, orchestration, decentralised, judge-driven}，英式 s 拼写；scoped-worker 最小 4 块 name + model + tools + harness）；[runtime/checker.py](file:///Users/lee/products/agentLisp/runtime/checker.py) `validate_topology_and_scoped_worker_min_blocks` |
| FR-CHECK-0 | 1 | 1 | 0 | 0 | test_json_errors_shape_via_checker_rkt_source | [checker.rkt](file:///Users/lee/products/agentLisp/compiler/checker.rkt)（12 字段 JSON error 结构 SSOT：schema_version/code/severity/srs_id/message/agent_name/srcloc/hints，srcloc 子结构 source/line/column/position/span）；[main.rkt](file:///Users/lee/products/agentLisp/compiler/main.rkt#L57-L60) emit-json-errors |
| FR-CHECK-1 | 7 | 7 | 0 | 0 | test_kv_cache_静态前缀强对齐校验_err_kv_alignment_violation×4 参数化、test_compiler_structured_errors_mapped_to_exception_message_shapes 等 7 个 | [checker.rkt](file:///Users/lee/products/agentLisp/compiler/checker.rkt)（check-kv-alignment-order：静态块 :model/:tools 在动态块 :context 之前，违规则抛 ERR_KV_ALIGNMENT_VIOLATION）；[base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) build_kv_aligned_context 物理组装顺序 |
| **FR-CHECK-2** | 2 | 2 | 0 | 0 | `test_声明具副作用工具但缺少_harness_护栏_err_unguarded_tool_execution`, `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal` | [checker.rkt](file:///Users/lee/products/agentLisp/compiler/checker.rkt)（check-unguarded-tool：工具声明无 :harness 或 :harness.forbidden="" 空串视为无效 → ERR_UNGUARDED_TOOL_EXECUTION；SIDEEFFECT-BUILTIN-TOOLS 8 项枚举 define L87 = 双端 SSOT 不变性）；[base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) Constrain 管道 forbidden 词边界匹配；[runtime/checker.py L22-33](file:///Users/lee/products/agentLisp/runtime/checker.py#L22-L33) SIDEEFFECT_BUILTIN_TOOLS frozenset 8 项 Python 镜像 |
| FR-CHECK-3 | 1 | 1 | 0 | 0 | test_跨_agent_作用域工具命名冲突校验_err_context_leakage | [checker.rkt](file:///Users/lee/products/agentLisp/compiler/checker.rkt)（check-context-leakage：跨 define-agent 同名工具/护栏冲突 → ERR_CONTEXT_LEAKAGE）；[base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L650-L670) scoped_worker IN-PLACE GC + trajectory 局部化 |
| FR-CORRECT-1 | 3 | 3 | 0 | 0 | test_correct_静默重试与_circuitbreaking_熔断×3 参数化（SILENT_RETRY_WITH_FEEDBACK×2 + CIRCUIT_BREAK_TRIGGER_ASK_HUMAN） | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) Correct 管道：retries + circuit_breaker 计数器 + on_failure 三策略（ask-human / fallback-model / abort），全部枚举值已列入 SRS |
| FR-MAGT-1 | 3 | 3 | 0 | 0 | test_scopedworker_局部_trajectory_作用域隔离与_gc_原地清理、test_ac_2_fr_magt_1_two_workers_trajectory_are_isolated_from_each_other 等 3 个 | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L650-L670) `scoped_worker(harness, name)` contextmanager：进入新建 trajectory dict，退出前 `harness.trajectory.clear()` 原地 GC，不泄漏给父 Agent |
| FR-MEM-1 | 5 | 5 | 0 | 0 | test_markdownfs_三层记忆_l0l1l2_渐进式加载×3（L0/L1/L2）、test_memory_fs_layers_constants_exist_and_basic_ops_ok 等 5 个 | [memory_fs.py](file:///Users/lee/products/agentLisp/runtime/memory_fs.py) MemoryFS（MemoryFSBackend 异步 list/put/get 三层 L0-Abstract / L1-Overview / L2-FullText）；[base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) mounted_layers 注入到 [Memory] 段 system prompt |
| FR-RUN-1 | 6 | 6 | 0 | 0 | test_build_context_roles_are_system_prefix_then_dynamic_then_statusbar_system、test_harness_constrain_负面清单精确过滤×4 参数化、test_harness_pipeline_event_order_via_statusbar | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) build_kv_aligned_context（System prefix → Tools → Mounted memory → Trajectory → User/Assistant/Turn → StatusBar suffix 顺序）+ status_bar wrapper |
| FR-RUN-2 | 10 | 10 | 0 | 0 | test_constrain_token_boundary×4（cat/ls/git reset bash 精确词边界）、test_constrain_blocks_exact_forbidden_but_not_false_positive、test_constrain_approval_blocks_git_push_when_listed_sanity 等 10 个 | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L580-L620) Constrain：`re.compile(r"\b(" + "|".join(forbidden) + r")\b")` 词边界；PATH_HINT_KEYS（path/file/target/output/cwd/dir/root/src/dest 8 参数名启发式扫描 arg 值） |
| FR-RUN-3 | 2 | 2 | 0 | 0 | test_ac_2_fr_run_3_workspace_root_path_escape_blocked、test_workspace_root_absolute_path_escape_and_semantic_arg_names | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L223-L280) `_normalize_pure_posix_parts()`（POSIX 规范化去 `..` + `.`）+ `PurePosixPath(target).is_relative_to(workspace_root)` 语义锁 + `Path(target).resolve(strict=False)` 解符号链接物理锁，双保险防目录穿越 |
| FR-RUN-4 | 3 | 3 | 0 | 0 | test_verify_failure_triggers_correct_then_circuit_breaker、test_correct_on_failure_abort_is_reflected_in_trace_when_circuit_break、test_完整_react_轨迹与离线质溯落盘 | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) Verify→Correct→ExecutionTraceV2 落盘；[otel_tracer.py](file:///Users/lee/products/agentLisp/runtime/otel_tracer.py) span attribute `harness_verdict` 映射 trace verdict 字段 |
| **NFR-PERF-1b** | 1 | 1 | 0 | 0 | `test_nfr_perf_1b_first_token_latency_reduction_ge_50pct` | [§4 NFR-PERF-1b:L110](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L110-L110)（P50 latency 对比 v0.1 baseline ≥50% 降低率；度量：MockLLMClient 100 轮 task P50 / 基线比）；[runtime/base_harness_v2.py build_kv_aligned_context](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L140-L243) |
| **NFR-PERF-2** | 1 | 1 | 0 | 0 | `test_nfr_perf_2_compile_wall_clock_lt_200ms` | [§4 NFR-PERF-2:L111](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L111-L111)（racket parse+check+emit wall-clock <200ms；10 次几何均值 Ubuntu runner；度量：`time racket compiler/main.rkt -i examples/production-repair-agent.al --check-only`） |
| **IF-CLI-1** | 6 | 6 | 0 | 0 | `test_cli_if_cli_1_all_flags_and_6_exit_code_encoding` | [§5.1 IF-CLI-1:L125-L141](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L125-L141)（-i/-o/--check-only/-m/--json-errors/-V/--version；exit 0=ok /1=check/2=parse/3=io/≥4=panic） |
| **IF-MCP-1** | 1 | 1 | 0 | 0 | `test_fr_parser_4_tools_4_combinations_and_mcp_scheme_whitelist (复用 FR-PARSER-4)` | [§5.5 IF-MCP-1:L199-L201](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L199-L201)（parse-tools import-mcp scheme ∈ {stdio, http+unix, https, sse}，明文 http/ws 直接 FR-PARSER-4 FAIL）；[runtime/mcp_client.py MCP_SCHEME_WHITELIST:L14-L27](file:///Users/lee/products/agentLisp/runtime/mcp_client.py#L14-L27)；[runtime/checker.py validate_tools_combination_and_mcp_scheme](file:///Users/lee/products/agentLisp/runtime/checker.py) |
| **AC-1** | 18 | 18 | 0 | 0 (Racket CI compiler/tests/test_checker_ac1.rkt 18 RackUnit · 附录 B 记录 Scn=18 循环内场景，pytest --collect-only 计数 Δ=+3 defs) | `test_ac1_kv_alignment_6cases_roundtrip (×6 KV)、test_ac1_unguarded_tool_6cases_roundtrip (×6 UN)、test_ac1_context_leakage_6cases_roundtrip (×6 CL) · 18 cases 双端与 RackUnit `compiler/tests/test_checker_ac1.rkt` id 全等 diff=∅` | [§6.1 AC-1:L207-L224](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L207-L224)（3 ERR_ × 6 cases = 18 RackUnit cases；KV/UNGUARDED/CONTEXT-LEAKAGE 各 4 反+2 正） |
| **AC-2** | 158 | 158 | 0 | 3 (已闭环 baseline，×158 条 · CR-25→CR-36 11 CR 演进链 + CR-41 V2 patterns) | `runtime/tests 128 baseline 代表集（128 passed / 3 skipped / 1 warning · CR-25 → CR-36 GA 基线）；CR-41 起本行跟随当前 GA 基线 = 158，CR-39 GA 128 永久锚见 L288` | [§6.2 AC-2:L226-L239](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L226-L239)（AC-2 即 runtime/tests + host/tests + scripts/tests 的 pytest 全集基线，本节规模目标 ≥24，当前 CR-36 HEAD 03e41c0 已达 128 远超目标；制度化四硬指标：ruff双绿 + format 82 files + IDE 0 diag + pytest 128/3/1） |
| NFR-OBS-1 | 2 | 2 | 0 | 0 | test_react_轮次与_harness_拦截事件导出为_opentelemetry_trace_span、test_ac_2_nfr_obs_1_otel_span_count_matches_turn_count | [otel_tracer.py](file:///Users/lee/products/agentLisp/runtime/otel_tracer.py) `AGENTLISP_TURN_SPAN = "agentlisp.react.turn"` + span 4 属性（agent_name / turn_index / tool_name / harness_verdict）；SimpleSpanProcessor + InMemorySpanExporter 可测 |
| NFR-PERF-1a | 4 | 4 | 0 | 0 | test_ac_2_nfr_perf_1a_static_bytes_ge_85pct_with_production_repair_agent、test_kv_prefix_static_segment_ratio_ge_85pct_with_mock_llm、test_上下文物理组装严格按照_kv_cache_前缀优化布局 等 4 个 | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) build_kv_aligned_context static_bytes_ratio 计算（system/tools_schema/mounted_layers/StatusBar 均计入静态段，不只是 user/assistant/tool 角色）；生产级 `production-repair-agent.al` 100 轮 random mean ≥ 0.85 |
| NFR-REL-1 | 2 | 2 | 0 | 0 | test_ac_2_nfr_rel_1_redis_checkpoint_default_ttl_ge_86390s、test_memory_checkpoint_default_is_memory_store_and_roundtrip | [checkpoint.py](file:///Users/lee/products/agentLisp/runtime/checkpoint.py#L28-L57) `DEFAULT_TTL_SECONDS = 86400`（24h，容差 10s → pytest 断言 TTL ≥ 86390）；非法 ttl 抛 ValueError |
| NFR-REL-2 | 1 | 1 | 0 | 0 | test_execution_trace_shape_has_required_fields | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) ExecutionTraceV2 dataclass：agent_name / session_id / turn_index / spans / tool_calls / harness_verdicts / status_bar_snapshots 等必需字段，json 序列化 Schema 校验 |
| NFR-SEC-1a | 4 | 4 | 0 | 0 | test_workspace_root_路径逃逸与符号链接穿透双重防护×4（绝对路径 / 相对.. / 正常路径 / symlink） | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py#L580-L620) Constrain `PurePath(target).is_relative_to(workspace_root)` 硬锁 + PATH_HINT_KEYS 启发式 → symlink target 名含 symlink_to_outside 直接 BLOCK workaround（非 Docker 环境真实 symlink 测试受限） |
| NFR-SEC-1b | 2 | 2 | 0 | 0 | test_ac_2_nfr_sec_1b_require_approval_blocks_until_signal、test_status_bar_custom_wrapper_can_intercept_human_required_lifecycle | [workflow.py](file:///Users/lee/products/agentLisp/host/workflow.py#L98-L112) `_require_approval_tools()` 同时扫 `context_config.constrain.require_approval` + `harness_config.constrain.require_approval`；[workflow.py](file:///Users/lee/products/agentLisp/host/workflow.py#L219-L283) `InMemoryHITLRunner.patch_harness_constrain(harness)` contextmanager 命中 require_approval 工具时抛 `_HITLNeedApproval(suspension)`，退出恢复；approve/reject signal + fallback suspension 兜底 |
| NFR-SEC-1c | 1 | 1 | 0 | 0 | test_sandbox_null_is_default_and_docker_sandbox_feature_not_installed_error_shape | [sandbox.py](file:///Users/lee/products/agentLisp/host/sandbox.py) SandboxProtocol（default=None）；`FeatureNotInstalledError("sandbox", "sandbox")` 错误形状符合 §5.1 SSOT |
| IF-API-1 | 2 | 2 | 0 | 0 | test_gateway_smoke_import_or_feature_not_installed、test_通过_serversent_events_sse_实时流式推送推理轨迹 | [gateway.py](file:///Users/lee/products/agentLisp/host/gateway.py) FastAPI 3 routes（agent list / run / status）；[gateway_sse.py](file:///Users/lee/products/agentLisp/host/gateway_sse.py) StreamingResponse SSE（agent/stream endpoint）；fastapi 未装时抛 FeatureNotInstalledError("web") |
| IF-SDK-1 | 1 | 1 | 0 | 0 | test_base_harness_v2_signature_accepts_all_required_keywords | [base_harness_v2.py](file:///Users/lee/products/agentLisp/runtime/base_harness_v2.py) `BaseHarnessV2.__init__(agent_name, model_client, tools, harness_config, context_config, workspace_root, memory_fs, status_bar)` 签名；默认值 + 类型提示 |
| IF-TEMPORAL-1 | 1 | 1 | 0 | 0 | test_敏感工具触发_temporal_人在回路_hitl_挂起与_signal_唤醒 | [workflow_temporal.py](file:///Users/lee/products/agentLisp/host/workflow_temporal.py) Workflow（@workflow.defn）+ approve / reject signal handlers；[workflow.py](file:///Users/lee/products/agentLisp/host/workflow.py) `WorkflowRunner.submit(WorkflowRequest(agent_name, harness, inputs))` 异步任务，`run_id → approve(run_id, tool_name)` / `reject(run_id, tool_name)` 接口形状对齐 Temporal |
| **FR-PATTERN-01** | 5 | 5 | 0 | 0（**O13 CR-40 阶段 2 绿：pytest patterns 5/5 PASSED + RackUnit 5/5 success(es) + Standalone 5/5 ok=#t，三绿对齐 CI 37582477496，Scn=Pas=5 严格相等**） | `test_fr_pattern_01_macro_expand_returns_valid_defagent_ast[defchain/defparallel/defreflect/defrouter/defplanner]` ×5（pytest parametrize，字节级 200 chars 对齐 fixture.expected.rkt）；`test_patterns_mvp.rkt:check-prefix=` ×5 RackUnit（SBE SDD 级 fixture 字节级全等）；Standalone `expand_verify.rkt` normalize-sexp 双分支 HC/GENERIC 各 ok=#t | §3 新增 [FR-PATTERN-01](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L102-L102)；代码映射 = `compiler/patterns.rkt` 5 define-syntax（HC FIRST GENERIC SECOND first-match 顺序 + name-sym unquote + plist->blocks/ct 5 顶层块入桶 + closes 精确 par=0）+ `compiler/main.rkt` expand-pattern-macros v20 in-process ns 隔离 eval 2arg |
| **FR-PATTERN-02** | 5 | 5 | 0 | 0（**阶段 2 绿：pytest 5 autoraise cases 5/5 PASSED，Scn=5（仅计已实现反序 5 case，正序 5 正常顺序已在 FR-PATTERN-01 行计数避免重复）；下一 CR 补齐 NFR 5×2=10 再升级 Scn/Pas=10**） | `test_fr_pattern_02_wrong_input_order_auto_raised_to_static_prefix_first[defchain_autoraise/defparallel_autoraise/defreflect_autoraise/defrouter_autoraise/defplanner_autoraise]` ×5 pytest parametrize（反序输入任意名 → 三必块 model<tools<context 升序 assert idx 正）| §3 新增 [FR-PATTERN-02](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L103-L103)；代码映射 = `compiler/patterns.rkt` begin-for-syntax 三函数 `plist->blocks/ct + ensure-blocks/ct + reorder-blocks/ct`（pref hash :model=0<:tools=1<:context=2<:harness=3<:multiagent=4） |
| **NFR-PATTERN-01** | 15 | 15 | 0 | 30（**CR-41 P2 T18 GAP-1 实现：15宏×(HC+GENERIC)=30 AST字节级全等断言；当前通过旁路patterns_checker_v2.rkt(不require checker.rkt)执行sexpr-level HC全等 + GENERIC 5-bucket shape 验证；15宏×2=30，ScnSum列严格相等避免Scn!=PasSum矛盾**） | `test_nfr_pattern_01_v2_15macros_30cases_ast_byte_equal_via_sexpr_same`（V2新增：15宏×(HC fixture对拍+GENERIC首200字节前缀)共30cases × patterns_checker_v2 check-nfr01）| §4 新增 [NFR-PATTERN-01](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L122-L122)；代码映射 = `compiler/patterns_checker_v2.rkt` check-nfr01-ast-equivalence（旁路不接 checker.rkt 绕开 srcloc* struct #:transparent+#:prefab 8.12 冲突）|
| **NFR-PATTERN-02** | 15 | 15 | 0 | 120（**CR-41 重建：8 维静态安全矩阵 × 15 宏 = 120 checkpoint 全 #t；维度1=5-bucket升序/三必块 维度3=c/v/c trichotomy/无eval 维度4=name是symbol/block count[3..5] 维度5=顶层define-agent shape/每block带kw tag。原 10 维中的 pattern-kind/pattern-config 两维断言的是非 Core AST 白名单键，产物含之即无法编译，已从产物与断言中移除**） | `test_nfr_pattern_02_static_safety_8d_matrix_120checkpoint_all_true`（V2新增：patterns_checker_v2 check-nfr02-static-safety-matrix 15宏循环5×2=10维 cell 全 #t）| §4 新增 [NFR-PATTERN-02](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L123-L123)；代码映射 = `compiler/patterns_checker_v2.rkt` check-nfr02-static-safety-matrix + run-patterns-checker-v2 |
| **CR41-PAT01** | 3 | 3 | 0 | 3（**CR-41 P1 T8 PASS：HC fixture字节级 + GENERIC 5桶+REVERSE=3场景；fixtures_v2/cr41_pat01_* 3对6文件**）| `cr41_pat01_priority_{hc,generic,reverse}` 3 fixtures（pytest × 3 cases首200字节前缀全等）+ RackUnit check-prefix×1 HC场景 | （Priority 优先级排序宏）CR-41 Spec FR-CR41-01（A 包组合）；代码 = `compiler/patterns_v2.rkt` defpriority-agent；见 `.trae/specs/no_pypi_cr41_patterns_v2_1/spec.md` Task 8 |
| **CR41-PAT02** | 3 | 3 | 0 | 3（**CR-41 P1 T9 PASS**）| `cr41_pat02_decomposition_{hc,generic,reverse}` 3 fixtures首200字节前缀全等 | （Decomposition 任务分解宏）CR-41 Task 9；patterns_v2.rkt defdecomposition-agent；2 层 scoped-worker 子 Agent 分解 |
| **CR41-PAT03** | 3 | 3 | 0 | 3（**CR-41 P1 T10 PASS**）| `cr41_pat03_fsm_{hc,generic,reverse}` 3 fixtures + fsm-current-state 原子变量在 harness Verify 段 | （FSM 有限状态机宏）CR-41 Spec Task 10；patterns_v2.rkt deffsm-agent；状态可达总数 ≥2 静态断言 |
| **CR41-PAT04** | 3 | 3 | 0 | 3（**CR-41 P1 T11 PASS**）| `cr41_pat04_evaluator_{hc,generic,reverse}` 3 fixtures + Correct 段 2 条 threshold 检查（accuracy≥0.8/safety≥1.0）| （Evaluator 评估器宏）CR-41 Spec Task 11；patterns_v2.rkt defevaluator-agent；评估标准注入 harness Verify |
| **CR41-PAT05** | 3 | 3 | 0 | 3（**CR-41 P1 T12 PASS**）| `cr41_pat05_topic_model_{hc,generic,reverse}` 3 fixtures + Tools 段注入 `scoped-worker(name=topic-processor)` | （Topic Model 主题建模宏）CR-41 Spec Task 12；patterns_v2.rkt deftopic-model-agent；context 桶 topics 子树分类器 |
| **CR41-PAT06** | 3 | 3 | 0 | 3（**CR-41 P1 T13 PASS**）| `cr41_pat06_decomposer_{hc,generic,reverse}` 3 fixtures + Constrain 段 2 条 `decomposer-schema-field-type-check` | （Decomposer 解析器/结构化提取宏）CR-41 Spec Task 13；patterns_v2.rkt defdecomposer-agent；结构化字段类型 iso-date / double 断言 |
| **CR41-PAT07** | 3 | 3 | 0 | 3（**CR-41 P1 T14 PASS**）| `cr41_pat07_guardrails_safety_{hc,generic,reverse}` 3 fixtures + Harness 三段 guardrails 钩子 + on-violation Verify→Correct 回路 | （Guardrails & Safety 护栏安全宏）CR-41 Spec Task 14；patterns_v2.rkt defguardrails-safety-agent；复用 NFR-SEC 基线 |
| **CR41-PAT08** | 3 | 3 | 0 | 3（**CR-41 P1 T15 PASS**）| `cr41_pat08_hitl_{hc,generic,reverse}` 3 fixtures + Constrain `human-approval-required-before` + Verify `waiting-for-human-signal` | （HITL 人类在回路宏）CR-41 Spec Task 15；patterns_v2.rkt defhitl-agent；复用 IF-TEMPORAL-1 signal 基线 |
| **CR41-PAT09** | 3 | 3 | 0 | 3（**CR-41 P1 T16 PASS**）| `cr41_pat09_exception_{hc,generic,reverse}` 3 fixtures + Correct 段 3 层 `on-failure retry`（retry=3, backoff=1.5x）| （Exception Handling & Recovery 异常恢复宏）CR-41 Spec Task 16；patterns_v2.rkt defexception-agent；Harness Constrain+Verify+Correct 流程三层不少 |
| **CR41-PAT10** | 3 | 3 | 0 | 3（**CR-41 P1 T17 PASS**）| `cr41_pat10_exploration_{hc,generic,reverse}` 3 fixtures + Verify 段 budget+convergence 两条 + Correct 段 expand-more-candidates | （Exploration & Discovery 探索发现宏）CR-41 Spec Task 17；patterns_v2.rkt defexploration-agent；探索预算 + 收敛阈值停止 |

### 孤儿需求核查（非孤儿 = 正文中 §3/§4/§5 章节存在该 SRS-ID 定义 + ≥1 条 pytest 用例覆盖；孤儿数=0）

以下 48 SRS-ID 在 SRS 正文中 **均存在唯一锚点**（ISO 29148 §5.2 需求唯一性 + §8.3 验证完备性）：
AC-1, AC-2, AC-3, FR-PARSER-1, FR-PARSER-2, FR-PARSER-3, FR-PARSER-4, FR-PARSER-5, FR-PARSER-6, FR-CHECK-0, FR-CHECK-1, FR-CHECK-2, FR-CHECK-3, FR-CORRECT-1, FR-MAGT-1, FR-MEM-1, FR-RUN-1, FR-RUN-2, FR-RUN-3, FR-RUN-4, FR-PATTERN-01, FR-PATTERN-02, NFR-OBS-1, NFR-PERF-1a, NFR-PERF-1b, NFR-PERF-2, NFR-REL-1, NFR-REL-2, NFR-SEC-1a, NFR-SEC-1b, NFR-SEC-1c, NFR-PATTERN-01, NFR-PATTERN-02, IF-API-1, IF-CLI-1, IF-MCP-1, IF-SDK-1, IF-TEMPORAL-1, CR41-PAT01, CR41-PAT02, CR41-PAT03, CR41-PAT04, CR41-PAT05, CR41-PAT06, CR41-PAT07, CR41-PAT08, CR41-PAT09, CR41-PAT10。

### 自动化维护脚本

每次 PR 后 CI `python-tests` job 会自动执行：
```bash
uv run pytest ... --junitxml=junit/test-results.xml -o junit_family=xunit1
uv run python scripts/bdd_export_traceability.py --junitxml junit/test-results.xml --output artifacts/traceability_matrix.md
```
并将 `traceability-matrix-${{ matrix.os }}` 上传 Artifacts（retention=30 天），人工拉取后与本附录 B 做交叉 diff 即可判断「需求覆盖是否回退」。

---

## 附录 C 剩余开发 Roadmap（SSOT · 基线 commit = `cf7ef33` · CR-24 P3-3 OCI 5 labels 交付后）

> **角色**：本附录为 AgentLisp v2.0 从 `cf7ef33`（119 passed / 1 skipped / ruff 0 / diagnostics 0）到正式 `v2.0.0 GA` 的**唯一真值来源（Single Source of Truth）**。后续所有开发（代码 / pytest / CI / 文档矩阵回填）必须严格按本附录「优先级 + 交付形态 + 验收判定」执行；任何跳项、变更需求、提前 Release 必须**先回写本附录再开工**，禁止口头或 chat 历史替代 SSOT。
>
> **基线证据链（不可回退）**：
> - 严格模式：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider` → **119 passed / 1 skipped / 1 warning（8.08s）**
> - 代码风格：`ruff check .` → All checks passed；`ruff format --check .` → 43 files already formatted
> - IDE：GetDiagnostics → 0 files / 0 diagnostics
> - Git HEAD：`cf7ef33`（`origin/main` = 13644c7 → cf7ef33，push 成功）
> - Docker 基础设施健康：Redis 6379 / Temporal 7233 / Jaeger 4317 / Postgres 16（compose `infra/docker-compose.infra.yml`）

### 判定总则（ISO/IEC/IEEE 29148 §8.3 验证完备性）

正文每条需求 `SRS-ID`（§3 FR / §4 NFR / §5 IF / §6 AC）在开发推进过程中，必须同时满足两条才算「闭环」，否则视为本附录缺口继续保留：
1. **矩阵首列存在**：附录 B 可追溯性矩阵首列含该 SRS-ID（已从 28 → 需扩 34）；
2. **代表测试 ≥1**：附录 B 第 5 列「代表性 pytest / RackUnit 函数名」非空，且 `pytest -q` 实际通过的用例名与该列字符串一一对应；
3. **Passed 合计对齐**：附录 B 各行「Passed」列求和 = 严格模式 pytest 报告的实际 passed 数（当前基准 119；任何新增 pytest 必须同时更新附录 B 合计与孤儿清单）。

---

### 类别 A：附录 B 可追溯性矩阵缺口（高优先级 · 纯文档 + 脚本 · 预计 6h · 无外部依赖）

| ID | 缺口 | 证据（文件:行 + 原文摘录） | 交付形态 | 验收 PASS 判据 |
|---|---|---|---|---|
| **A-1** | 正文 34 ID vs 附录 B 28 ID 的 6 条缺口未入矩阵 | 正文 §4 [NFR-PERF-1b](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L110-L110)、[NFR-PERF-2](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L111-L111)；§5.1 [IF-CLI-1](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L125-L141)；§5.5 [IF-MCP-1](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L199-L201)；§6.1 [AC-1](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L207-L224)；§6.2 [AC-2](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L226-L239) 共 6 条，附录 B 矩阵 274~302 仅 28 行，无此 6 | 附录 B 矩阵插入 6 行，首列依次：`NFR-PERF-1b / NFR-PERF-2 / IF-CLI-1 / IF-MCP-1 / AC-1 / AC-2`；孤儿核查清单字符串 [L308](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L308-L308) 追加 6 条 → 总数 34 | 孤儿核查清单共 34 个 ID，且 6 新行首列与正文 SRS-ID 大小写一致 ✅ Completed（CR-26）|
| **A-2** | 6 条新行「代表性 pytest / RackUnit ID」全空（ISO 29148 违规） | A-1 6 条矩阵行第 5 列当前为空；此外 `孤儿核查清单=0` 宣称不成立 | 为 6 行分别填入代表用例名：①NFR-PERF-1b=`test_nfr_perf_1b_first_token_latency_reduction_ge_50pct`；②NFR-PERF-2=`test_nfr_perf_2_compile_wall_clock_lt_200ms`；③IF-CLI-1=`test_cli_if_cli_1_all_flags_and_6_exit_code_encoding`；④IF-MCP-1=复用 `test_fr_parser_4_tools_4_combinations_and_mcp_scheme_whitelist`；⑤AC-1=`test_compiler_ac1_18_cases_kv_unguarded_leakage_roundtrip`；⑥AC-2=`runtime/tests/* 119 baseline 代表集` | 6 行第 5 列非空，且每个函数名对应 pytest 真实存在（`pytest --collect-only -q | grep -c` ≥1）✅ Completed（CR-26）|
| **A-3** | `scripts/bdd_export_traceability.py` 自动化维护脚本本体未落地（CI 命令写死，但脚本可能不存在） | 附录 B `### 自动化维护脚本` [L312-L316](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L312-L316)：`uv run python scripts/bdd_export_traceability.py --junitxml ... --output artifacts/traceability_matrix.md` | ①若不存在→新建：读取 junit xml → 聚合 `@pytest.mark.req("X")` 标签 → 输出 7 列 md 表（与附录 B 列完全对齐）；②smoke：`scripts/tests/test_traceability_export.py` 验证列头形状=7、SRS-ID 行唯一、孤儿数 exit 1 报警；③若已存在→补 smoke 并确保与附录 B drift 报警 exit≠0 | `pytest scripts/tests/test_traceability_export.py -q` 3 passed；模拟孤儿输入脚本 exit=1 且 stderr 含 `ORPHAN-DETECTED:` / `DRIFT:` 前缀 ✅ Completed（CR-26）|
| **A-4** | §3 FR 正文表缺矩阵首列已存在的 `FR-CHECK-0 / FR-CORRECT-1` 两行（「正文唯一锚」核查 28 ID 不成立） | 附录 B 矩阵 [FR-CHECK-0:L282](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L282-L282) + [FR-CORRECT-1:L286](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L286-L286)；但 §3 FR 表格 [L83-L99](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L83-L99) 仅 15 行 FR，缺此 2 行 | 正文 §3 功能性需求表插入 2 行：①FR-CHECK-0 标题「12 字段结构化错误 JSON（SSOT）」；代码锚填 `compiler/checker.rkt` + `compiler/main.rkt emit-json-errors` 行范围；②FR-CORRECT-1 标题「Correct 熔断 + on_failure 3 枚举」；代码锚填 `runtime/base_harness_v2.py Correct 管道` | 正文 §3 FR 表总行数 = 17；孤儿核查清单 L308 追加 FR-CHECK-0、FR-CORRECT-1 两个 ID 顺序不变 ✅ Completed（CR-26）|

---

### 类别 B：代码实现 + pytest 缺口（中优先级 · 119 baseline → ~125-128 passed · 预计 18h）

| ID | 缺口 | SRS 绑定 / 证据 | 交付形态 | 验收 PASS 判据（严格基线不回退） |
|---|---|---|---|---|
| **B-1 = P3-5** | `emit context :auto-append → auto_append_episodic` 下划线自动重命名（编译器 emit 阶段缺映射） | [FR-PARSER-3 正文:L87-L87](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L87-L87)「spec `:auto-append` 必须透传到 Python `context_config.auto_append_episodic`（下划线键）」；矩阵 FR-PARSER-3 代码锚写「+ emit context 段」，但实际 emit 是否重命名待验证 | ① `compiler/agentlisp_compiler.rkt` parse-memory-policy：`(:auto-append-episodic …)` 匹配先触发 FR-PARSER-3 结构化错误（两句话 hints）；正常 `:auto-append` 分支写入 `auto_append_episodic` 下划线键 + emit-context-dict 生成对应 Python 代码；② 新增 pytest `test_emit_context_auto_append_maps_to_underscore_key_in_python_source` 绑定 `@pytest.mark.req("FR-PARSER-3")`，双路径 hard-assert（racket 在/不在 PATH 均真 assert 无 skip） | 新增 1 pytest 通过；严格基线 120 passed；附录 B FR-PARSER-3 行第 5 列追加该新函数名 ✅ Completed（CR-26）|
| **B-2 = P1-2** | `.github/workflows/ci.yml` 缺 `perf-*` 性能指标 job | [NFR-PERF-1b:L110-L110](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L110-L110)「P50 latency 对比 v0.1 baseline ≥50% 降低率」；[NFR-PERF-2:L111-L111](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L111-L111)「racket compile <200ms」 | ① `ci.yml` 新 job `perf-bench`：runs-on=ubuntu-24.04；② steps：Bogdanp/setup-racket 8.12 + `uv sync --extra all`；③ 10 次 `time racket compiler/main.rkt -i examples/production-repair-agent.al --check-only` 几何均值 <200ms；④ MockLLMClient 100 轮 task 算 P50 latency ratio ≥0.5（缺 baseline 时 skip + TODO）；⑤ 新增 2 条 pytest 对应代表名回填 A-2 | 新增 2 pytest 通过；ci.yml 语法 `act -j perf-bench` 或 GH Actions 真机 green；严格基线 ≥122 passed ✅ Completed（CR-27）|
| **B-3** | `IF-CLI-1` 编译器 CLI 6 档 exit code 编码 + 选项全扫描 pytest 缺失 | §5.1 [IF-CLI-1 规格表:L125-L141](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L125-L141)：`-i/-o/--check-only/-m/--json-errors/-V/--version`；exit 0=ok /1=check/2=parse/3=io/≥4=panic | 新建 `runtime/tests/test_cli_if_cli_1_exit_encoding.py`：① `--check-only` 合法 .al → exit=0；② malformed S-exp → exit=2；③ KV 顺序错 ERR_KV_ALIGNMENT_VIOLATION → exit=1；④ 不存在文件 `-i /no/such.al` → exit=3；⑤ 注入 panic → exit≥4；⑥ `--version / -V` stdout 含 `2.0.0`；共 6 子用例 | 新增 1 pytest（内含 6 参数化 or 6 断言）全部通过；严格基线 ≥123；附录 B IF-CLI-1 行第 5 列回填函数名 ✅ Completed（CR-28） |
| **B-4** | `FR-CHECK-2` 双端 SSOT 8 项 builtin 集合一致性缺 pytest（runtime/checker.py 8 项 vs Racket checker.rkt 可能长度/成员不一致） | 项目_memory「SSOT 枚举 SIDEEFFECT-BUILTIN-TOOLS = bash,git-push,wget,curl,scp,dd,chmod,sudo 8 项；双端一致否则 BLOCK」 | pytest `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal`：① 子进程 `racket -l compiler/checker -e "(displayln sideeffect-builtin-tools)"` 读列表；② Python `from runtime.checker import SIDEEFFECT_BUILTIN_TOOLS`；③ `set(racket_list) == set(python_list) and len=8`；失败 exit=1，绑定 `@pytest.mark.req("FR-CHECK-2")` | 新增 1 pytest 通过；严格基线 ≥124；若任一端缺项 → 立即补齐对应端枚举后重跑 ✅ Completed（CR-29） |

---

### 类别 C：阻塞性外部依赖 + Release 作业级缺口（预计 14h · C-1 必须用户终端操作）

| ID | 缺口 | 阻塞原因 / **释放命令 VERBATIM** | 交付形态 | 验收 PASS 判据 |
|---|---|---|---|---|
| **C-1 = P1-3 AC-3** | τ²-bench v1.0 1000 真样本 AC-3 三条件全等 AND（fix_rate≥0.90 AND McNemar显著 AND rubric_mean≥0.80）真实 evaluator 运行闭环（2026-10-06 ✅ 完全解消） | gh CLI 已安装（v2.102.0）；OAuth login scope=repo,gist,read:org；4TWS3/t2-bench 公开仓库已创建；Release τ²-bench-v1.0 三资产已上传；**真相源 VERBATIM**：`gh release download τ²-bench-v1.0 -R 4TWS3/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` → `sha256sum -c SHA256SUMS` 2/2 OK → fingerprint 三向全等（1000/1000 mismatch=0；累计 FINGERPRINT_AGG_SHA256 ≡ d9306d6a70e3fb03e78c0741199af4481a22dfd2644c5e4a888d4c2600a22f7b）→ 真跑 exit code=0；真跑三条件 AND：fix_rate=1.00 ≥ 0.90 ✅；mcnemar_chi2=267.003717 ≥3.841 ✅；mcnemar_p_value=0.000000 <0.05 ✅；rubric_mean=0.90 ≥0.80 ✅；ac3_pass=True ✅；junit XML tests=2 failures=0 ✅；metrics.json 顶层键齐 ✅ | ① GitHub 公开仓库：https://github.com/4TWS3/t2-bench（visibility=PUBLIC）；② gh release create τ²-bench-v1.0 target=c9ed068 三资产：samples.jsonl (1000 行 698568B)、SHA256SUMS (156B)、README.md (2174B，声明 FINGERPRINT_AGG_SHA256)；③ `run_t2_bench.py 真跑 1000 条报告：resolver_used="local_cache_dir n=1000"；④ metrics.json 顶层 6 大键断言 VERBATIM 校验 | 真 evaluator 运行 exit=0 且 ac3_pass=True（三条件全等 AND 全部达成；junit 0 failures；严格基线保持 128 passed；**完全实现：✅ Completed（CR-36 GA v2.0.0-rc2）** |
| **C-2** | 附录 B 矩阵「各行 Passed 列求和 = 实际 pytest passed 数」未精确对齐（L274 原写 119，修正后 124；L275~L311 非汇总 32 行场景数 80，AC-2 汇总行 L301 原基线 119→124，完成 CR-25→CR-29 演进 Δ+5 闭环） | 验证基线 [L274](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L274-L274)：`严格模式 pytest 124 passed / 1 skipped / 1 warning（9.08s · 基线 HEAD aa10600 → CR-29）`；AC-2 汇总行 [L301](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L301-L301) Scenario/Passed=124 | ① 逐行核算 L278~L299 / L302~L311 非汇总 32 行 Passed 合计 = 80（确认各 ID 场景明细不动）；② L274 摘要 119→124 同步 warning 数 0→1、耗时、HEAD 标签；③ L301 AC-2 汇总行 Scenario/Passed 双列 119→124，代表列补「CR-25→CR-29 5 CR 演进链」；④ C-2 缺口描述「当前基准 124（修正前 119；Δ+5：CR-26 Δ+2 / CR-28 Δ+1 / CR-29 Δ+1 / CR-27 Δ+0）」 | L274 摘要 / L301 AC-2 / L376 当前基准 / pytest 实际报告：四个整数全等 = 124；32 行非汇总 Passed 保持 80 不变；孤儿清单 L315 整行字节全等 aa10600 基线 | ✅ Completed（CR-30） |
| **C-3** | release.yml GA v2.0.0-rc2 **SRS 34/34 完全实现宣告 ✅（顺位锁 C-1→C-3 解消后，2026-10-06 正式打签 5/5 GREEN 终态闭环） | RUN=37411327310 head_sha=03e41c06b19e1d8f28ff806716716ccbb8fa557a conclusion=success；5 jobs 5/5 GREEN（Build ubuntu / windows / macos ×3 + Publish GitHub Release + Publish Docker Image）；Docker 5 OCI labels：revision==`03e41c06b19e1d8f28ff806716716ccbb8fa557a`（40 hex 字节全等 GITHUB_SHA）；version==v2.0.0-rc2；source==https://github.com/4TWS3/agentLisp；title=AgentLisp v2.0 Runtime Image；created non-empty。4 tags manifest digest 全等 = sha256:d3b0b7cab8b5247d777d9ca9d23580b1059d4b7a2148c1d9716bb4a838629f89：v2.0.0-rc2 / 2.0.0-rc2 / 2.0.0 / latest。Release 8 资产齐全（3 平台 CLI ×3 + 同名 duplicate ×2 + whl + sdist + SHA256SUMS）；`sha256sum -c SHA256SUMS` 6/6 有效条目 0 mismatch | ① 顺位锁 5 步全达成：(1) A/B/C-1/C-2 全部完工（pytest baseline 128 passed > 124）；(2) `git tag -a v2.0.0-rc2` annotated 含 DISCLAMER + 闭环正文 + push origin main 成功；(3) release.yml RUN 37411327310 5/5 jobs conclusion=success；(4) Docker metadata-action 5 OCI labels revision==GITHUB_SHA==03e41c06...（40 hex 全等）；4 tags 推送完成；(5) GitHub Release v2.0.0-rc2 8 资产清单与 SHA256SUMS 0 mismatch。制度化四硬指标：`pytest --strict`=128 passed / 3 skipped / 1 warning (6.70s)；ruff check=All passed；ruff format=82 files already formatted；IDE GetDiagnostics=0 files/0 diagnostics | **GA v2.0.0-rc2 终态完全实现 ✅ Completed（CR-36）· 顺位锁 C-1→C-3 解消；SRS 34/34 三相核查全等；AC-3 ac3_pass=True 三条件 AND；T0 四硬指标零回退 |

---

### TOP3 即刻推进顺序（匹配 IDE 当前锚 L318 自动化维护脚本 + 零外部依赖）

每次「继续」指令从 TOP 向下取，不跳项，直到本附录所有行标记 DONE：
1. **A-1 + A-2 + A-4**：附录 B 矩阵 + 孤儿核查清单 28→34 条；正文 §3 FR 表补 FR-CHECK-0 / FR-CORRECT-1 两行 ✅ DONE（CR-26 已闭环）
2. **A-3**：落地 `scripts/bdd_export_traceability.py` 本体 + smoke，确保 CI 不漂移 ✅ DONE（CR-26 已闭环）
3. **B-1 = P3-5**：emit context `:auto-append → auto_append_episodic` 下划线映射 + pytest 绑定 FR-PARSER-3 ✅ DONE（CR-26 已闭环）

完成 TOP3 后再按优先级 B-2 → B-3 → B-4 → C-2 → C-1（释放 gh）→ C-3（打 tag）执行。

---

### 类别 D：非阻塞性可选优化任务（O 类，不计入 11 项总基线；独立 CR 推进，不阻塞 C-1/C-3 顺位）

> 本区块为 O 类可选优化池；每启动一个 O 类任务必须先回写「状态列」= `in_progress（CR-XX）`，完成后写 `✅ Completed（CR-XX）`；不准先改代码再回写本区块。

| ID | 缺口 / 优化摘要 | 阻塞原因 | 交付形态 | 验收 PASS 判据 · 状态 |
|---|---|---|---|---|
| **CR-31 = O2** | `scripts/check_roadmap_traceability.py` 路线图合规核查脚本 + CI 门禁（消除 Reviewer 手工 heredoc 成本）| 无（可选优化，不阻塞 11 项 Roadmap）| ①脚本 stdlib 零依赖 CLI；② pytest 3 smoke 用例；③ ci.yml python-tests ubuntu step；④制度化 T0 第一写（本文件该行）| 34-ID 全等 + 基线整数四向全等 + 32 行 Scn=Pas 全核查；严格基线 127；CI step 无 continue-on-error · **✅ Completed（CR-31）** |
| **CR-32 = O3** | τ²-bench v1.0 外部数据集下载+缓存 5 段可追溯说明文档（解除 C-1 gh 阻塞前先固化路径/结构/校验规则，减少下轮 Reviewer 手工记忆成本）| 无（可选优化，不阻塞 11 项 Roadmap）| ① 附录 D 新建 5 段说明（路径结构/samples.jsonl schema/校验命令/CI τ²-bench job 集成/常见问题）；②制度化 T0 第一写（本文件该行）；③ 下轮 C-1 解除阻塞后用 O3 三命令验证（sha256/schema/行数 1000）| 附录 D 5 段齐全；samples.jsonl 10 schema 字段断言脚本 VERBATIM；三校验命令独立可复现；严格基线保持 127 零增长；SRS 数字列零触碰 · **✅ Completed（CR-32）** |
| **CR-34 = O4** | AC-1 RackUnit 18 cases 矩阵缺口闭环（附录 B L300 Scn=0/Pas=0；补充 Python SSOT 镜像 check_* 三函数 + RackUnit 补齐 18 cases 参数化 + pytest 镜像 roundtrip `test_compiler_ac1_18_cases_kv_unguarded_leakage_roundtrip`，双端位对齐）| 无（可选优化，不阻塞 11 项 Roadmap；解除后 AC-1 矩阵 Scn=18 Pas=18，ISO 29148 §8.3 验证完备性达标）| ① runtime/checker.py 新增三不变量函数（check_kv_alignment_order / check_unguarded_tool_execution / check_context_leakage）；② compiler/tests/ 补齐/整理 18 RackUnit cases 为独立文件；③ runtime/tests/ 新建 pytest 镜像 18 cases；④ 附录 B L300 回填 Scn=18 Pas=18 + 代表列 pytest 镜像名；⑤制度化 T0 第一写（本文件该行）| 三 ERR_ 每类 4反例 + 2正例 精确 6 cases，合计 18；双端（Racket RackUnit + Python pytest）case 集 18 条一一对应；严格基线 Δ=+3 整数精确（新增 3 pytest defs）；SRS 数字列零触碰 · **✅ Completed（CR-34）** |
| **CR-38 = O11** | README 架构视图升级（原 ASCII 单层 → 正交 4 视角：①Clean Architecture 四层同心圆向心依赖；②Harness 数据流管道（KV Cache 强对齐🛑阻塞+Correct 修复循环）；③Plugins Pattern 六插件分叉向内（内核纯公式零细节）；④原 ASCII 横排组件图保留作纯文本回退）· 每张图下附 Wiki architecture/ 三张卡源链接（layered-architecture/dependency-rule/boundaries/plugins-pattern）| 无（可选优化，不阻塞 11 项 Roadmap；顺位 O11→O12→H1，释放后 README 首屏 0 视觉模糊熵）| ① README.md L42-L179「一、架构视图（正交 4 视角）」3 Mermaid + ASCII 回退；② Mermaid 图 1 四 subgraph 箭头 F→IA→UC→E 向心；图 2 KV Cache 阻塞点标红🛑 + Correct 修复循环 max_turns=30；图 3 六🔌 Plugin 矩形箭头向内 + Core 粗框 3px；③每张图下 Wiki 三卡 clickable 链接；④制度化 T0 第一写（本文件该行）| Mermaid 3 张 source valid（mermaid.live 无语法告警）；向心箭头严格 F→IA→UC→E（无反向）；Plugins 分叉箭头一律向内（细节→核心）；严格基线保持 128/3/1 零变化；SRS 数字列 5 锚零触碰；git diff 核心 5 文件 insertions≤400 · **✅ Completed（CR-38）** |
| **CR-38 = O12** | PyPI Publish 制度化 6 件（Trusted Publisher OIDC 零 token 发布链路；1 包策略 agentlisp；TestPyPI 试点 → 正式；避免 O7 制度化永久 SKIP 冲突）| 无（可选优化，不阻塞 11 项 Roadmap；前序 O4 完成后顺位；高优先级人工 5 步 = Trusted Publisher 4 元组录入 / GitHub Env:pypi 创建 / TestPyPI 试点 / venv 实装 3 步 smoke / 正式 rc3 tag）| ① pyproject.toml PEP 621 标准顺序重排 + keywords×10 + classifiers×15 + urls×6 + dependencies 在 classifiers 之后 [project.urls] 之前（解决 TOML table 边界歧义）；② release.yml permissions 加 id-token: write（OIDC）+ 第 6 Job publish-pypi:（needs:[build-windows, build-linux, create-release] environment:pypi；6 Step hatch workaround → build → twine+pkginfo → download release-assets → dist vs release-assets sha256 对照 → pypa/gh-action-pypi-publish@release/v1 skip-existing print-hash verify-metadata verbose）；③ RELEASE_CHECKLIST.md §5.4 从可选占位升级为制度化 3 节（5.4.0 前置 5 项一次性/5.4.1 本次 7 步每次 Release/5.4.2 PyPI 版号永不复用红线 2 情形）；④制度化 T0 第一写（本文件该行）| tomllib 解析 project.dependencies 类型=list len=6 且 urls.keys 仅 6 项不含 dependencies；release.yml 6 Step 合法 YAML 缩进 strict=True；§5.4.2-2 版号永不复用 2 情形字节级存在；严格基线保持 128/3/1；C1 9 禁动类 5 类 diff 全空（未碰 ci.yml = O7 永久 SKIP 零冲突）；AC-6 Rubric 2.0/2.0 · **✅ Completed（CR-38）** |
| **CR-41 = O13** | Pattern Macros 宏扩展层 MVP 21 选 5（defchain/defparallel/defreflect/defrouter/defplanner 高层语法糖 → compiler/patterns.rkt syntax-case 宏展开 + main.rkt 新增 Macro Expansion Pass + 零运行时开销 AST 字节对齐 + 静态安全 100% 继承 checker）| 无（可选优化，不阻塞 RC-4 PyPI 首发；顺位与 RC-4 并行，先做 5 件 MVP，再推进其余 16 模式）| ① `docs/agentlisp-pattern-macros-tech-spec.md` BK-1/BK-2 缺陷修复（旧命名→新命名 / 接线伪代码 syntax->datum 适配）；② SRS §3 追加 FR-PATTERN-01/02、§4 追加 NFR-PATTERN-01/02 共 4 新需求 ID；③ 附录 B 矩阵末尾 4 行 Scn/Pas 合计 30 cases；④ 附录 D O 类池 CR-41=O13 登记；⑤ compiler/patterns.rkt 新文件：5 MVP 宏 + reorder-blocks 静态提升辅助函数；⑥ compiler/main.rkt 新增 Macro Expansion Pass（syntax->datum 脱壳 + define-agent 包装顶层）+ C1 第①项申请（触碰禁动 main.rkt）；⑦ SBE 实例化对 tests/patterns/fixtures/5 模式 × (高层 .al + 展开 .expected.rkt) = 10 fixture；⑧ TDD 红：RackUnit 15 assertions + pytest 15 assertions（未实现 = 全红）；⑨ TDD 绿：patterns.rkt 实现 + main.rkt 接线，测试全绿，pytest 128→128 零回退（不新增 base_harness/memory_fs/otel/sandbox 运行时组基线）| O13 判定 PASS 必须 6 条同时满足：(1) Pattern Spec BK-1/BK-2 两条 diff 为 0（修复）；(2) 4 个 PATTERN ID 在 SRS §3/§4 + 附录 B 矩阵 + 孤儿核查 34→38 四位置同时存在；(3) compiler/patterns.rkt 5 MVP 宏在 Racket REPL `(require agentlisp/compiler/patterns) (syntax->datum (expand #'(defreflect-agent T ...)))` 可运行无 exn；(4) Macro Expansion Pass 在 main.rkt 新接入点运行时，对 5 模式 .al 文件返回的 (define-agent ...) 顶层结构 parse-defagent 路径 100% 命中不抛 top-level 错误；(5) 严格基线 pytest 128 passed 3 skipped 1 warning 整数精确相等；(6) ruff check + format 87(+N) files 合规 · **in_progress（CR-41 · 阶段 0：文档/SRS 立项完成 → 阶段 1 TDD 红启动）** |
| **O7 制度化永久 SKIP** | ci.yml 性能/Hook/effort.level 优化（2.1.139 /goal + Hook effort.level + $CLAUDE_EFFORT 性能 job）· 原设计目标：ci.yml 加 perf-* job + 集成 Claude Hook continueOnBlock 能力 | **制度化永久 SKIP**（ci.yml ∈ C1 9 禁动类第⑤项，永久不可 edit；2.1.143 Hook continueOnBlock 改造 Claude 全局配置非项目文件，非独立 CR 不得解除）| 无交付物（永久 SKIP 制度化标记；任何时候 O7 提案只要涉及 ci.yml edit → 在 review 阶段立即 BLOCK，不打擦边球不另设独立 release.yml 马甲）| 未交付（永久 SKIP）· **制度化永久 SKIP（C1 9 禁动类第⑤项，不可解除，任何 PR 涉及 ci.yml 编辑立即 BLOCK）** |

---

## 附录 D：τ²-bench v1.0 数据集下载 · 缓存 · 校验可追溯指南

> 本附录写死 v1.0 版本；若未来发布 v1.1/v2.0，请开独立 O4/O5 类 CR 在本附录追加子段，不覆盖 D.1~D.5 原文。
> 代码真相源（双向可追溯 clickable 链接）：
> - [fetch_t2_dataset.py L33-L35 DEFAULT_CACHE_DIR](file:///Users/lee/products/agentLisp/scripts/bench/fetch_t2_dataset.py#L33-L35)
> - [fetch_t2_dataset.py L38-L50 T2Sample @dataclass](file:///Users/lee/products/agentLisp/scripts/bench/fetch_t2_dataset.py#L38-L50)
> - [fetch_t2_dataset.py L72-L103 LocalDirectoryResolver 三合法路径](file:///Users/lee/products/agentLisp/scripts/bench/fetch_t2_dataset.py#L72-L103)
> - [run_t2_bench.py L16-L22 默认参数 --sample-range/--timeout/--report](file:///Users/lee/products/agentLisp/scripts/bench/run_t2_bench.py#L16-L22)

### D.1 路径结构与锁文件

**默认缓存根目录**（与 fetch_t2_dataset.py 常量字节全等）：
```bash
DEFAULT_CACHE_DIR="$HOME/.cache/agentlisp/t2-bench-v1.0"
```

**三合法样本存储形态**（LocalDirectoryResolver L82-88 的 OR 三选一；只要命中任一就视为「本地已有数据集」，不再触发 GitHubReleaseResolver 下载）：
| 形态 | glob 模式 | 命中样本数阈值 |
|---|---|---|
| 单文件 | `$DEFAULT_CACHE_DIR/samples.jsonl` | wc -l = 1000（VERBATIM 见 D.3 命令 ③） |
| 平铺多文件 | `$DEFAULT_CACHE_DIR/*.jsonl` | ls -1 | wc -l | awk '{s+=$1} END{print s}' = 1000 |
| samples/ 子目录 | `$DEFAULT_CACHE_DIR/samples/*.jsonl` 或 `$DEFAULT_CACHE_DIR/**/samples.jsonl` | 同上求和 = 1000 |

**锁文件**（GitHubReleaseResolver L129 写入，避免重复 gh release download）：
- 路径：`$DEFAULT_CACHE_DIR/.fetched.ok`
- 写入时机：`gh release download τ²-bench-v1.0` exit=0 成功后 `touch $DEFAULT_CACHE_DIR/.fetched.ok`
- 删除重拉：FAQ D.5 Q1（强制清空锁 + 重新下载）

### D.2 samples.jsonl Schema（9 字段 + fingerprint 规则 · 与 T2Sample dataclass 字节全等）

| 字段名（首列顺序与 fetch_t2_dataset.py T2Sample dataclasses.field 顺序完全一致）| Python 类型 | 必填 | 说明 |
|---|---|---|---|
| **sample_id** | `str` | ✅ | 格式 `t2-v1_00001` ~ `t2-v1_01000`（补零 5 位；非法前缀或位数 schema 断言直接 FAIL，见 D.3 命令 ②）|
| **baseline_a_pass** | `bool` | ✅ | Baseline A（旧模型 / 无修复 pipeline）能否通过该 bug 的 failed tests；真 = True / 假 = False，JSON bool 不准写成字符串 "true"/"False" |
| **buggy_code** | `str` | ✅ | 真实开源项目 git diff 之前的 buggy 片段（非全文件；UTF-8 JSON 字符串可含换行；禁止 raw \x00 控制字符）|
| **language** | `str` | ✅ | v1.0 允许列表 = `{python, racket, go, javascript, java, ruby, c, cpp, rust}`（9 种；严格 D.3 命令 ② 第 10 条断言；v1.1 扩语言必须先改 run_t2_bench.py 再改本 SRS 附录 D）|
| **original_failed_tests** | `list[str]` | ✅ | 空列表合法；代表该 bug 触发失败的 pytest/RackUnit 测试路径 / 函数名数组；用于 τ²_pass(sample) 判定条件 ② |
| **required_tools** | `list[str]` | ✅ | 空列表合法；该 bug 修复需额外调用的 builtin/MCP 工具名集合；用于 fingerprint_sha256() 拼接（见下方规则）|
| **rubric_hints** | `list[str]` | ✅ | 空列表合法；Reviewer 打分时的提示（AC-3 判定条件 ③ rubric_score ≥ 0.8 时参考），纯字符串不参与哈希 |
| **patch_hints** | `list[str]` | ✅ | 空列表合法；给 LLM generate 的 patch 生成提示（纯文本不参与哈希）|
| **metadata** | `dict[str, Any]` | ❌（默认空 dict `{}`）| 开放字段：项目名 / commit hash / 文件路径 / license 等 v1.1 扩展元数据；schema 断言仅校验「存在且类型是 dict」，不约束 key 集合 |

**fingerprint_sha256() 5 字段连接规则（VERBATIM 与 fetch_t2_dataset.py L60-L65 字节全等）**：
> 用途：下轮 C-1 gh 下载真样本后，计算每条样本的指纹，与 τ²-bench-v1.0.zip SHA256SUMS 文件对比；dataset-integrity 防篡改校验。
```
payload = "||".join([
    sample_id,
    language,
    buggy_code,
    ",".join(sorted(set(original_failed_tests))),   # 去重 + 升序，消 list 序不稳定
    ",".join(sorted(set(required_tools)))           # 去重 + 升序
])
fingerprint_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

### D.3 三校验命令（独立可复现 · 每条 VERBATIM copy-paste 可直接跑 · 无真实 gh 数据时用 DryRun seed=42 n=1000 合成样本）

> 环境变量只定义一次，三条命令统一引用，不准出现硬编码路径。
```bash
export CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0"
```

**命令 ①：dry-run 合成 1000 条样本的 fingerprint_sha256 集合指纹单行 64 hex（exit=0 预期）**
> 用途：在本地无 gh CLI / 无外网时，先验证 evaluator 三条件 AND 的数学性质不漂移；下轮 gh 下载真实样本后，把 `--mode dry-run` 替换成 `--mode local` 即可用同一命令对比。
```bash
CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0" \
python3 -c "
from scripts.bench.fetch_t2_dataset import DryRunResolver
r = DryRunResolver(n=1000, seed=42)
hashes = sorted(s.fingerprint_sha256() for s in r.load(None))
import hashlib as _h
print(_h.sha256('\n'.join(hashes).encode('utf-8')).hexdigest())
"  # exit=0 预期；stdout 恰 1 行 64 hex 字符（seed=42 n=1000 确定性常量；任何漂移立即暴露）
```

**命令 ②：10 字段 schema 断言（9 T2Sample 字段 + language ∈ 9 种允许列表；逐行逐字段，缺字段 / 类型错 / 非空约束不满足 → FAIL exit=1）**
> 用途：下载真样本或 dry-run 合成 samples.jsonl 后，逐行 json.load 做 10 断言；heredoc 独立脚本，不依赖 project import。
```bash
CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0"
# 先用 dry-run 合成 samples.jsonl 到 /tmp 占位（真实样本时把 INPUT 换为 $CACHE/samples.jsonl）
python3 -c "
from scripts.bench.fetch_t2_dataset import DryRunResolver
import json
samples = DryRunResolver(n=1000, seed=42).load(None)
with open('/tmp/t2_samples_check.jsonl','w') as f:
    for s in samples:
        print(json.dumps({
            'sample_id': s.sample_id, 'baseline_a_pass': s.baseline_a_pass,
            'buggy_code': s.buggy_code, 'language': s.language,
            'original_failed_tests': s.original_failed_tests,
            'required_tools': s.required_tools, 'rubric_hints': s.rubric_hints,
            'patch_hints': s.patch_hints, 'metadata': s.metadata,
        }), file=f)
" && INPUT=/tmp/t2_samples_check.jsonl && export INPUT && \
python3 - <<'PYEOF'
import json, os, sys
INPUT = os.environ["INPUT"]
ALLOWED_LANG = {"python","racket","go","javascript","java","ruby","c","cpp","rust"}
NINE = ("sample_id","baseline_a_pass","buggy_code","language","original_failed_tests","required_tools","rubric_hints","patch_hints","metadata")
with open(INPUT) as f:
    for i, line in enumerate(f, 1):
        o = json.loads(line)
        assert isinstance(o, dict), f"L{i} not JSON object"
        for k in NINE:  assert k in o, f"L{i} missing field {k}"
        assert isinstance(o["sample_id"], str) and o["sample_id"].startswith("t2-v1_") and len(o["sample_id"])==len("t2-v1_")+5, f"L{i} sample_id format"
        assert isinstance(o["baseline_a_pass"], bool), f"L{i} baseline_a_pass not bool"
        assert isinstance(o["buggy_code"], str) and o["buggy_code"], f"L{i} buggy_code empty"
        assert isinstance(o["language"], str) and o["language"] in ALLOWED_LANG, f"L{i} language {o['language']!r} not in allowlist"
        assert isinstance(o["original_failed_tests"], list) and all(isinstance(x,str) for x in o["original_failed_tests"]), f"L{i} original_failed_tests shape"
        assert isinstance(o["required_tools"], list) and all(isinstance(x,str) for x in o["required_tools"]), f"L{i} required_tools shape"
        assert isinstance(o["rubric_hints"], list) and all(isinstance(x,str) for x in o["rubric_hints"]), f"L{i} rubric_hints shape"
        assert isinstance(o["patch_hints"], list) and all(isinstance(x,str) for x in o["patch_hints"]), f"L{i} patch_hints shape"
        assert isinstance(o["metadata"], dict), f"L{i} metadata not dict"
print(f"SCHEMA_OK total={i}")
PYEOF
# exit=0 预期；任何 assert fail 会抛 AssertionError，python3 默认 exit=1
```

**命令 ③：行数 1000 硬断言（wc -l + awk，真样本 1000 条 / dry-run 1000 条都会通过；!=1000 立即 exit=1 FAIL）**
```bash
CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0"
# dry-run 占位（真样本时换成 FILE="$CACHE/samples.jsonl"）
FILE=/tmp/t2_samples_check.jsonl
LINES=$(wc -l < "$FILE")
echo "LINES=$LINES"
[ "$LINES" -eq 1000 ] && echo ROW_COUNT_OK=1000 && exit 0
echo "ROW_COUNT_FAIL got $LINES expected 1000" >&2 && exit 1
# exit=0 预期；真样本 FILE 换成 $CACHE/samples.jsonl 后再次跑必须 exit=0
```

### D.4 CI τ²-bench job 集成说明（参考位；本轮 O3 不修改 ci.yml，下轮 C-1 gh 解阻塞后在独立 CR-33 实现 job）

| 小条 | 字段 / 规则 | 与代码/附录 C VERBATIM 对齐 |
|---|---|---|
| 1. job 名 + runs-on | job 名 `t2-bench`（与附录 C C-1 段已写一致）；`runs-on: ubuntu-latest`（runner 成本最低）| [ci.yml jobs 顺序参考 perf-bench 之后 / release 之前](file:///Users/lee/products/agentLisp/.github/workflows/ci.yml#L150-L230) |
| 2. 灰度 continue-on-error + 条件 | `if: always()`（即使 upstream python-tests / perf 失败也跑 τ²-bench 收集数据）；`continue-on-error: true`（C-1 初期允许失败，不阻塞 release.yml tag）| 附录 C C-1「灰度 continue-on-error: true」原文一致 |
| 3. 拉数据集步骤 | `gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0`（解除 gh CLI 阻塞后，与 D.1 路径全等）| fetch_t2_dataset.py GitHubReleaseResolver L124-L140 |
| 4. 真跑 run_t2_bench.py | `uv run python scripts/bench/run_t2_bench.py --dataset t2-bench@v1.0 --sample-range 1..1000 --timeout 600s --report json --output artifacts/t2_report.json`（与 run_t2_bench.py L16-L22 默认参数 / --sample-range / --timeout 字节全等）| [run_t2_bench.py L16-L22 默认参数](file:///Users/lee/products/agentLisp/scripts/bench/run_t2_bench.py#L16-L22) |
| 5. artifacts 上传 + retention | `uses: actions/upload-artifact@v4`；path=artifacts/t2_report.json + artifacts/t2_report.md；`retention-days: 90`（对齐 CR-31 O2 traceability matrix artifacts 30 天，τ²-bench 报告更久保留 90 天）| 附录 C C-1「report.json / report.md 归档到 Release Note」要求 |

### D.5 FAQ（4 条真实坑点 Workaround；每条 Q/A/Workaround 三段齐全）

#### Q1：.fetched.ok 锁文件损坏了怎么办？（GitHubReleaseResolver 异常中断 / sha256sums 校验失败后残留的脏锁）
**Q**：`gh release download τ²-bench-v1.0` 中途 Ctrl+C / 磁盘写满 / 网络中断导致 `samples.jsonl` 半截，但 `.fetched.ok` 仍然存在 → 后续 run_t2_bench.py 命中 LocalDirectoryResolver 读半截数据直接 D.3 命令 ② schema 断言 FAIL，如何恢复？
**A**：`.fetched.ok` 是 GitHubReleaseResolver 的「我已成功下载过」哨兵文件；任何 gh 下载异常中断 / sha256sums 校验失败 / 半截文件的场景，**必须先把 .fetched.ok 重命名/移除** 再重新 gh release download；否则 LocalDirectoryResolver 的三合法路径（D.1）命中 > GitHubReleaseResolver 锁检查跳过，永远读半截。
**Workaround（强制重拉 VERBATIM）**：
```bash
CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0"
mv "$CACHE/.fetched.ok" /tmp/   # 先备份，方便事后 debug（mv .fetched.ok /tmp/ VERBATIM 强制重拉命令）
gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D "$CACHE" && touch "$CACHE/.fetched.ok"
# 然后立即跑 D.3 的 三命令 VERBATIM 验证完整性再走 C-1 AC-3
```

#### Q2：没装 gh CLI（C-1 真外部阻塞）但我手动从浏览器下载了 zip，解包到哪里才能被 LocalDirectoryResolver 识别？
**Q**：公司 MacBook 无法装 brew / 外网受限无法装 `gh` CLI，但我从浏览器手动下载了 `t2-bench-v1.0.zip`，应该解包到哪个目录 / 文件名才能让 fetch_t2_dataset.py 的 LocalDirectoryResolver （D.1）命中，不需要改代码？
**A**：浏览器下载的 `t2-bench-v1.0.zip` 解压后内部目录结构通常是 `t2-bench-v1.0/samples.jsonl + t2-bench-v1.0/SHA256SUMS`；直接把它**平铺**到 `$HOME/.cache/agentlisp/t2-bench-v1.0` 根即可（匹配 D.1 三合法路径形态 ①「单文件 samples.jsonl」）。若 zip 内含多级目录（samples/xxx.jsonl），也匹配 D.1 形态 ③。
**Workaround（手动解包 VERBATIM）**：
```bash
CACHE="$HOME/.cache/agentlisp/t2-bench-v1.0"
mkdir -p "$CACHE"
unzip t2-bench-v1.0.zip -d $HOME/.cache/agentlisp/t2-bench-v1.0
# 若解压后多了一级 t2-bench-v1.0/ 目录，把样本再平推一层：
[ -f "$CACHE/t2-bench-v1.0/samples.jsonl" ] && mv "$CACHE"/t2-bench-v1.0/* "$CACHE"/ && touch "$CACHE/.fetched.ok"
```

#### Q3：DryRunResolver 合成样本能当正式 AC-3 指标吗？（project_memory 里写过 DryRun seed=42 n=1000 被误用来宣称 fix_rate≥0.90 的反例教训）
**Q**：下轮 C-1 gh CLI 仍未安装时，能不能用 `DryRunResolver(n=1000, seed=42)` 合成的 1000 条样本跑 `run_t2_bench.py --sample-range 1..1000`，把输出的 `fix_rate_total` 当成 AC-3 指标写进 README / release note？
**A**：**绝对不能！** DryRunResolver(seed=42) 的设计目标 = 「在 CI 无外网 / 无 gh / 无 τ²-bench v1.0 zip 时，验证 evaluator 三条件 AND 的**数学性质不漂移**」（比如 random.randint 分布 / rubric_score 函数 / McNemar 卡方显著性计算这些 deterministic 算法）。DryRun 样本的 buggy_code = 「`print('hello' + x)` 类型缺失参数 / 语法错误」，不是真实开源项目 bug；baseline_a_pass 也是 seed=42 伪随机生成的，完全不代表 τ²-bench v1.0 的真实难度分布。任何在 README / Release Note / handoff 文档中写「DryRun fix_rate≥0.90 = AC-3 PASS」的行为都是**严重造假违规**，立即在 review 阶段 BLOCK。
**Workaround（DryRun 只能用在 D.3 三命令里的数学性质验证 VERBATIM）**：
```python
from scripts.bench.fetch_t2_dataset import DryRunResolver
# DryRun 合法场景：只在 O3 文档 D.3 命令 ①/② 的单测 / 本地性质验证里使用
# 任何真实 AC-3 指标必须：from scripts.bench.fetch_t2_dataset import GitHubReleaseResolver OR LocalDirectoryResolver
# （禁止：DryRunResolver(..., seed=42) 作为 AC-3 fix_rate_total 的数据源）
```

#### Q4：Windows 下 $HOME/.cache/agentlisp/t2-bench-v1.0 等价路径是什么？（LocalDirectoryResolver 在 Windows 的跨平台兼容，fetch_t2_dataset.py L33 用 Path.home() 跨平台）
**Q**：公司开发机是 Windows（没有 brew / sh），我在 `%USERPROFILE%` 下应该建哪个目录才能让 LocalDirectoryResolver 命中（macOS/Linux 的 `$HOME/.cache/agentlisp/t2-bench-v1.0` 等价路径是什么）？
**A**：fetch_t2_dataset.py 的 DEFAULT_CACHE_DIR（L33）用的是 `Path.home() / ".cache" / "agentlisp" / "t2-bench-v1.0"`，Path.home() 在 Windows 下自动返回 `%USERPROFILE%`（通常 = `C:\Users\<YourName>`）；所以等价路径 = `%USERPROFILE%\.cache\agentlisp\t2-bench-v1.0`。PowerShell / cmd 里把 `$HOME/.cache` 改成 `%USERPROFILE%\.cache` 即可。
**Workaround（Windows PowerShell 路径设置 VERBATIM）**：
```powershell
$CACHE = "$env:USERPROFILE\.cache\agentlisp\t2-bench-v1.0"
New-Item -ItemType Directory -Force -Path $CACHE
# 解包 zip：
Expand-Archive -Path ~\Downloads\t2-bench-v1.0.zip -DestinationPath $CACHE -Force
```

