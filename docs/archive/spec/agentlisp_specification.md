# AgentLisp 语言完整规范与设计文档 (v2.0)

> 基于《深入理解 AI Agent：设计原理与工程实践》核心架构理论  
> 核心公式：**Agent = Model + Harness**

---

## 一、 语言设计哲学与核心理念

`AgentLisp` 是一门面向 AI Agent（智能体）领域的声明式 DSL（Domain-Specific Language），基于 S-表达式（S-expression）设计。

### 1.1 核心公式与关注点分离
在现代 AI Agent 工程中，Agent 的本质可以形式化为：
$$\text{Agent} = \text{Model} + \text{Harness}$$
其中：
$$\text{Harness} = \text{上下文管理} + \text{工具接口} + \text{约束 (Constrain)} + \text{验证 (Verify)} + \text{纠正 (Correct)}$$

`AgentLisp` 遵循严格的**关注点分离（Separation of Concerns）**与**架构克制**原则：
* **`AgentLisp` 声明**：Agent 的决策大脑 (`:model`)、观察空间与记忆 (`:context`)、动作工具 (`:tools`) 以及 Harness 三重安全护栏 (`:harness`)。
* **宿主环境 (Host Environment) 承载**：网络网关 (FastAPI)、长流程持久化 (Temporal)、容器沙箱 (Docker/E2B)、分布式链路追踪 (OpenTelemetry)。

### 1.2 为什么选择 S-表达式与 Lisp 范式？
* **同构性（Homoiconicity）**：数据即代码，代码即数据。在 Agent 架构中，Prompt/上下文既是模型读取的数据，又是驱动模型决策的指令。
* **REPL 与 ReAct 的契合**：Lisp 的 REPL (Read-Eval-Print Loop) 循环与 Agent 的 ReAct (Observation-Reasoning-Action-Verify) 循环具有天然的灵魂契合。

---

## 二、 内置架构规约 (Language Primitives)

`AgentLisp v2.0` 将《深入理解 AI Agent》书中的最佳架构实践固化为语言级特性与编译器检查断言：

1. **KV Cache 静态前缀强对齐 (Static Prefix Alignment)**
   - 语法强制要求 `:model` 和 `:tools`（静态前缀）写在 `:context`（动态轨迹）之前，确保最大化命中 LLM 供应商的 KV Cache，降低 50%+ 的首 Token 延迟。
2. **Harness 一等控制流 (Harness as First-Class Control Flow)**
   - 不存在无防护的“裸工具调用”。未显式声明 `:harness` 块时，编译器会自动注入默认安全与断言中间件。
3. **词法上下文作用域 (Lexical Context Scoping)**
   - 提供 `scoped-worker` 原语。子 Agent 在独立的作用域内运行，其中间数十轮冗长的 ReAct 轨迹在作用域结束时自动垃圾回收 (GC)，绝不污染主 Agent 的上下文。
4. **Markdown 记忆数据结构与惰性加载**
   - 原生支持 `:markdown-fs` 记忆模型，提供 `L0-Abstract`（摘要）、`L1-Overview`（概览）、`L2-FullText`（全文）分层原语，运行时按需惰性加载（Lazy Loading）。
5. **状态栏尾部 Hook (Trailing Context Hook)**
   - 原生绑定 `:status-bar`，在每轮 Trajectory 渲染末尾自动挂载 `<agent_status>` 标签，解决长对话下模型“遗忘目标”的问题。

---

## 三、 形式化语法规范 (EBNF Grammar)

```ebnf
(* AgentLisp v2.0 顶层声明：强制 StaticBlock 在 DynamicBlock 之前 *)
AgentDecl         ::= "(" "defagent" AgentName StaticBlock DynamicBlock HarnessBlock [MultiAgentBlock] ")"
AgentName         ::= Symbol

(* 1. 静态前缀块：静态提升 (Static Prefix Hoisting) 以最大化 KV Cache 命中 *)
StaticBlock       ::= ModelClause ToolsClause
ModelClause       ::= "(" ":model" ModelProperty+ ")"
ModelProperty     ::= ":provider" String
                    | ":name" String
                    | ":temperature" Number
                    | ":system-prompt" (String | TextBlock)

ToolsClause       ::= "(" ":tools" ToolStatement+ ")"
ToolStatement     ::= "(" "import-builtin" Symbol+ ")"
                    | "(" "import-mcp" String ")"
                    | "(" "define-tool" ToolName ToolSpec ")"

(* 2. 动态轨迹与上下文块 *)
DynamicBlock      ::= "(" ":context" ContextProperty+ ")"
ContextProperty   ::= ":memory" MemorySpec
                    | ":skills" "(" Symbol* ")"
                    | ":status-bar" "(" StatusBarItem+ ")"
                    | ":compression" CompressionSpec

MemorySpec        ::= "(" ":markdown-fs" PathString ":layers" "(" MemoryLayer+ ")" [":auto-append" Boolean] ")"
MemoryLayer       ::= 'L0-Abstract | 'L1-Overview | 'L2-FullText
StatusBarItem     ::= ":step-count" Boolean | ":time-tracker" Boolean | ":todo-list" Boolean | CustomKV

(* 3. Harness 三重工程护栏块 *)
HarnessBlock      ::= "(" ":harness" HarnessGuard+ ")"
HarnessGuard      ::= "(" "constrain" ConstrainProp+ ")"
                    | "(" "verify" VerifyProp+ ")"
                    | "(" "correct" CorrectProp+ ")"

ConstrainProp     ::= ":forbidden-commands" "(" String+ ")"
                    | ":require-human-approval" "(" Symbol+ ")"
                    | ":workspace-root" PathString

VerifyProp        ::= ":json-schema" Boolean
                    | ":linter-check" Boolean
                    | ":test-runner" String
                    | ":reviewer-agent" Symbol

CorrectProp       ::= ":max-retries" Integer
                    | ":circuit-breaker" Integer
                    | ":on-failure" ('ask-human | 'fallback-model | 'abort)

(* 4. 词法上下文隔离的多 Agent 块 (Lexical Scope) *)
MultiAgentBlock   ::= "(" ":multiagent" ":topology" TopologyType [":workers" "(" ScopedWorker+ ")" ] ")"
ScopedWorker      ::= "(" "scoped-worker" WorkerName StaticBlock HarnessBlock ")"
WorkerName        ::= Symbol
TopologyType      ::= 'peer | 'orchestration | 'decentralized | 'judge-driven
```

---

## 四、 编译器不可变规约 (Compiler Invariants)

Racket/Python 编译器在 AST 编译期强制执行以下错误判定：

* **`ERR_KV_ALIGNMENT_VIOLATION`**：动态 `:context` 块出现在静态 `:model` 或 `:tools` 块之前。
* **`ERR_UNGUARDED_TOOL_EXECUTION`**：具副作用的工具未挂载 `constrain` 拦截或 `verify` 断言。
* **`ERR_CONTEXT_LEAKAGE`**：`scoped-worker` 内部轨迹跨作用域溢出至全局。

---

## 五、 模块与语法配置详解

### 5.1 `:model` 模块
* `:provider`：LLM 供应商标识（如 `"anthropic"`, `"openai"`, `"qwen"`）。
* `:name`：特定模型名称（如 `"claude-3-7-sonnet"`）。
* `:temperature`：采样随机度（`0.0` - `1.0`）。
* `:system-prompt`：核心角色定位与原则。

### 5.2 `:tools` 模块
* `import-builtin`：导入标准内置工具，如 `read-file`, `edit-file`, `bash`, `code-interpreter`。
* `import-mcp`：挂载标准 **MCP (Model Context Protocol)** 服务，如 `"stdio://python ./mcp_server.py"`。
* `define-tool`：声明本地轻量脚本工具。

### 5.3 `:context` 模块
* `:memory`：挂载 Markdown 文件系统，包含层级配置 `(L0-Abstract L1-Overview L2-FullText)`。
* `:skills`：离线 Skill 指南目录引用。
* `:status-bar`：配置尾部追加的 `<agent_status>` 属性（步骤数、耗时、待办列表）。

### 5.4 `:harness` 模块
* **`constrain`（约束）**：违禁命令负面清单（如 `"rm -rf"`）、高危操作人在回路授权（如 `git-push`）及沙箱根路径。
* **`verify`（验证）**：结构化 Schema 断言、静态 Linter 检查、Pytest 自动化测试套件、Reviewer Agent 对抗审查。
* **`correct`（纠正）**：静默重试上限、连续失败熔断阈值及终态降级策略（`ask-human`, `fallback-model`, `abort`）。

### 5.5 `:multiagent` 模块
* `:topology`：多 Agent 拓扑形态（`orchestration` 编排模式、`peer` 对等模式、`judge-driven` 法官驱动模式等）。
* `scoped-worker`：声明上下文强隔离的子智能体。

---

## 六、 完整代码范例

```lisp
;; =====================================================================
;; AgentLisp v2.0 完整生产级范例：代码修复智能体
;; =====================================================================

(defagent production-repair-agent

  ;; 1. 静态前缀块 (KV Cache 对齐)
  (:model
    :provider "anthropic"
    :name "claude-3-7-sonnet"
    :temperature 0.2
    :system-prompt "你是一个严谨的代码修复 Agent。原则：先读取记忆，修改代码，再跑测试断言。")

  (:tools
    (import-builtin read-file edit-file bash grep)
    (import-mcp "stdio://python ./mcp_servers/github_mcp.py"))

  ;; 2. 动态上下文块 (包含 Markdown 记忆与状态栏 Hook)
  (:context
    :memory (:markdown-fs "./workspace"
             :layers (L0-Abstract L1-Overview L2-FullText)
             :auto-append #t)
    :skills (python-debugging)
    :status-bar (:step-count #t :time-tracker #t :todo-list #t))

  ;; 3. Harness 三重工程护栏
  (:harness
    (constrain
      :forbidden-commands ("rm -rf /" "git reset --hard")
      :require-human-approval (git-push)
      :workspace-root "./workspace")
    (verify
      :json-schema #t
      :linter-check #t
      :test-runner "pytest tests/")
    (correct
      :max-retries 3
      :circuit-breaker 5
      :on-failure ask-human))

  ;; 4. 多 Agent 上下文隔离
  (:multiagent
    :topology 'orchestration
    :workers
    ((scoped-worker test-runner-worker
       (:model :provider "anthropic" :name "claude-3-5-haiku" :temperature 0.0)
       (:tools (import-builtin bash))
       (:harness (verify :test-runner "pytest"))))))
```

---

## 七、 运行时与云原生集成架构

```
 AgentLisp (DSL 源代码 .al)
          │
          ▼ (Racket / Python 编译器)
 生产级 Python 运行时代码 (base_harness.py)
          │
          ├─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
   FastAPI 网关 (HTTP/SSE)    Temporal 工作流 (持久化/HITL)  E2B/Docker 沙箱 (安全隔离)
```

1. **FastAPI Web 网关**：包装为 HTTP POST/SSE 接口，向前端输出流式 Reasoning 与 Tool Result。
2. **Temporal 工作流**：触发 `:require-human-approval` 时自动将当前栈帧挂起落盘，等待 Signal 唤醒。
3. **E2B / Docker 沙箱**：工具在隔离容器中执行，防止宿主环境污染。
4. **OpenTelemetry**：自动向 Jaeger/Langfuse 导出包含 LLM 推理与工具调用的分布式 Trace。
