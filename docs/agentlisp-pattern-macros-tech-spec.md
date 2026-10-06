# AgentLisp 设计模式宏扩展层 (Pattern Macros) 技术交底与实现规范

> **面向研发 Agent (Coding Agent) 的技术落地与交付规范**  
> **版本**：v2.1.0-spec  
> **核心架构**：分层 DSL 宏展开（Pattern Macros → AgentLisp Core AST → Python Runtime）  
> **理论依据**：《深入理解 AI Agent：设计原理与工程实践》 + Antonio Gulli《智能体设计模式》

---

## 1. 项目背景、目的与总体工程目标

### 1.1 核心痛点与背景
`AgentLisp v2.0` 当前已具备严密的静态编译器（`compiler/agentlisp_compiler.rkt`）与 Harness 物理护栏运行时（`runtime/base_harness_v2.py`），实现了基于 $\text{Agent} = \text{Model} + \text{Harness}$ 架构公式的底层基础设施。

然而，当开发者构建复杂的工业级 Agent 时，直接编写底层的 Core DSL 表达式（显式配置 `:model`、`:context`、`:tools`、`:harness` 及其十余项嵌套属性）面临以下工程瓶颈：
* **重复代码冗余 (Boilerplate Noise)**：常见的生成者-批评者反思（Reflection）、条件路由（Routing）、多任务并行（Parallelization）等经典模式需要重复编写几十行结构高度相似的 Harness 嵌套代码。
* **模式复用困难**：业界成熟的 21 种 Agentic 设计模式（如 Antonio Gulli Handbook 中总结的范式）缺乏语言级的一等公民（First-Class Citizen）抽象。
* **安全规约与开发体验的博弈**：若让开发者随意封装 Python 胶水代码，容易绕过 AgentLisp 编译器强行的 `ERR_KV_ALIGNMENT_VIOLATION`（静态前缀对齐）与 `ERR_UNGUARDED_TOOL_EXECUTION`（裸工具防护）硬性静态断言。

### 1.2 总体工程目标
本规范旨在指导 Coding Agent 在 `compiler/` 目录下新增 `patterns.rkt` 模块，为 AgentLisp 注入**两层宏编译架构 (Two-Layer Macro Expansion Architecture)**：
1. **开发者体验 (DX) 目标**：实现 80% 的经典场景下，开发者仅需使用 10 秒钟编写 5–10 行高层模式语法糖（Pattern Macros）即可定义复杂的 Agent 系统。
2. **零运行时开销 (Zero-Cost Abstraction)**：所有高层模式语法糖在 Racket 编译期通过 `syntax-case` 宏系统完全展开为标准的 AgentLisp Core AST，运行时无任何反射或解释器损耗。
3. **100% 静态安全继承**：高层模式宏展开后的 AST 必须无条件继承 AgentLisp 编译器的所有物理安全断言，包括 KV 静态前缀对齐、沙箱路径锁以及高危命令拦截负面清单。

---

## 2. 分层 DSL 与宏展开架构

### 2.1 架构层次设计
AgentLisp 采用**分层编译解耦**架构，将高层编排表达力与底层物理安全护栏完全分离：

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │   1. 上层：Pattern Macros DSL (21 种模式高层声明)                       │
 │   例如: (defreflect-agent ...), (defrouter-agent ...), (defplanner ...)│
 └───────────────────────────┬────────────────────────────────────┘
                                     │ 编译期宏展开 (Racket Macro Expansion)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │   2. 中层：AgentLisp Core AST (静态规约与物理 Harness)                   │
 │   标准 S-表达式: (defagent name (:model ...) (:context ...) (:harness ...))│
 └───────────────────────────┬────────────────────────────────────┘
                                     │ 静态检查与 Python 代码转译 (Checker & Transpiler)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │   3. 底层：Python Runtime & 云原生宿主胶水层                             │
 │   BaseHarnessV2 + FastAPI SSE + Temporal Workflow + E2B Sandbox        │
 └────────────────────────────────────────────────────────────────────────┘
```

### 2.2 宏展开与安全继承机制
Racket 编译前端在处理输入文件时，首先通过 `compiler/patterns.rkt` 导出的模式宏进行表达式展开。宏转换器（Macro Transformer）承担“结构化安全注入”的职责：

* **静态前缀强制提升 (Static Hoisting)**：不论高层宏的参数编写顺序如何，宏展开后的 AST 必须强行保证 `:model` 与 `:tools` 写在动态 `:context` 之前，彻底解决 KV Cache 错位问题。
* **默认安全护栏兜底 (Default Safety Injection)**：高层宏展开时，会自动为未显式配置安全项的模式注入标准的 `Constrain` 负面清单（如拦截 `rm -rf`、`dd`、`mkfs`）与 `Correct` 熔断参数（如上限 3 次重试，连续失败 5 次熔断）。

---

## 3. 21 种 Agentic 设计模式的 DSL 抽象与 AST 降维映射规约

Coding Agent 必须在 `compiler/patterns.rkt` 中实现以下 5 大类共 21 种设计模式的高层宏抽象，并确保能够精准展开为 AgentLisp Core AST。

### 3.1 核心控制与执行流模式 (Core Control & Execution Flow)

#### 1. 提示链 (Prompt Chaining)
* **高层 EBNF 语法**：
  ```ebnf
  DefChain ::= "(" "defchain-agent" AgentName ":steps" "(" StepSpec+ ")" ")"
  StepSpec ::= "(" ":prompt" String [ ":in" Symbol ] [ ":out" Symbol ] ")"
  ```
* **用户高层声明**：
  ```lisp
  (defchain-agent doc-pipeline
    :steps ((:prompt "提取文档摘要" :out summary)
            (:prompt "基于摘要生成代码" :in summary :out code)))
  ```
* **Core AST 展开映射**：展开为单个 `defagent`，将其转换为系统提示词中步骤依赖链，并在 `:harness` 中注入多步顺序断言。

#### 2. 路由 (Routing)
* **高层 EBNF 语法**：
  ```ebnf
  DefRouter ::= "(" "defrouter-agent" AgentName ":model" ModelSpec ":routes" "(" RouteSpec+ ")" ")"
  RouteSpec ::= "(" ":intent" QuoteSymbol "=>" WorkerName ")"
  ```
* **用户高层声明**：
  ```lisp
  (defrouter-agent ops-gateway
    :model ("openai" "gpt-5.6")
    :routes ((:intent 'db-query  => db-worker)
             (:intent 'net-debug => net-worker)))
  ```
* **Core AST 展开映射**：展开为具有 `:multiagent :topology 'orchestration` 节点的 AST，主 Router 包含分发 Prompt，Worker 节点映射为独立的 `scoped-worker`。

#### 3. 并行化 (Parallelization)
* **高层 EBNF 语法**：
  ```ebnf
  DefParallel ::= "(" "defparallel-agent" AgentName ":branches" "(" BranchSpec+ ")" ":reducer" ReducerName ")"
  ```
* **用户高层声明**：
  ```lisp
  (defparallel-agent multi-search
    :branches ((search-a "来源 A") (search-b "来源 B"))
    :reducer aggregator-agent)
  ```
* **Core AST 展开映射**：展开为 `:multiagent` 并发节点，多个 `scoped-worker` 并行拉起，最终轨迹进入 `aggregator-agent` 归并。

#### 4. 规划 (Planning)
* **高层 EBNF 语法**：
  ```ebnf
  DefPlanner ::= "(" "defplanner-agent" AgentName ":model" ModelSpec ":planner-prompt" String ":executor-tools" "(" ToolId+ ")" ")"
  ```
* **用户高层声明**：
  ```lisp
  (defplanner-agent deep-researcher
    :model ("anthropic" "claude-3-7-sonnet")
    :planner-prompt "将研究目标分解为 3-5 个步骤"
    :executor-tools (web-search read-pdf))
  ```
* **Core AST 展开映射**：在 `:model` 中注入 CoT 计划生成 Prompt，并在 `:harness (:verify ...)` 中挂载计划完成度断言。

#### 5. 优先级排序 (Prioritization)
* **高层 EBNF 语法**：
  ```ebnf
  DefPrioritized ::= "(" "defprioritized-agent" AgentName ":criteria" "(" Symbol+ ")" ")"
  ```
* **Core AST 展开映射**：在 `:context` 的 `:status-bar` Hook 中注入 `:todo-list #t`，并在每次 ReAct 步前注入依据 `:criteria` 动态排序的提示策略。

---

### 3.2 环境交互与工具模式 (Environmental Interaction & Tools)

#### 6. 工具使用 / 函数调用 (Tool Use / Function Calling)
* **语法映射**：对应 AgentLisp 标准 `:tools (import-builtin ...)` 节点，编译期强制检查 ACI 工具规范。

#### 7. 模型上下文协议 (Model Context Protocol, MCP)
* **语法映射**：对应 `:tools (import-mcp "http://endpoint/mcp")`，转译为 Python 端的 MCP 异步 Client 连接器。

#### 8. 智能体化 RAG (Agentic RAG)
* **高层 EBNF 语法**：
  ```ebnf
  DefRAG ::= "(" "defrag-agent" AgentName ":kb-path" PathString ":layers" "(" Layer+ ")" ")"
  ```
* **Core AST 展开映射**：自动展开为 `:context (:memory-policy (:markdown-fs path :layers layers :auto-append-episodic #t))` 惰性加载结构。

#### 9. 智能体间通信 (A2A Communication)
* **高层 EBNF 语法**：
  ```ebnf
  DefA2A ::= "(" "defa2a-server" AgentName ":agent-card-id" String ")"
  ```
* **Core AST 展开映射**：为 Agent 追加 FastAPI A2A 协议头与 Agent Card 描述暴露入口。

#### 10. 推理技术 (Reasoning Techniques)
* **高层 EBNF 语法**：
  ```ebnf
  DefReasoning ::= "(" "defreasoning-agent" AgentName ":technique" QuoteSymbol [ ":beam-width" Integer ] ")"
  ```
* **Core AST 展开映射**：根据 `'tree-of-thought` 或 `'react` 参数，在 `:model` 的 `system-prompt` 中植入树状探索或 CoT 推理结构。

---

### 3.3 状态、反思与自适应模式 (State, Reflection & Adaptive)

#### 11. 反思 / 自我纠错 (Reflection / Self-Correction)
* **高层 EBNF 语法**：
  ```ebnf
  DefReflect ::= "(" "defreflect-agent" AgentName ":provider" String ":model-name" String ":tools" "(" ToolId+ ")" ":critic" String ":max-retries" Integer ")"
  ```
* **用户高层声明**：
  ```lisp
  (defreflect-agent code-refiner
    :provider "anthropic" :model-name "claude-3-7-sonnet"
    :tools (bash pytest) :critic "检查代码逻辑漏洞" :max-retries 3)
  ```
* **Core AST 展开映射**：展开为完整的 `defagent` 结构，将 `:critic` 自动挂载至 `:harness (:verify :reviewer-agent critic)`，并将 `:max-retries` 写入 `:correct` 节点。

#### 12. 记忆管理 (Memory Management)
* **高层 EBNF 语法**：
  ```ebnf
  DefMemory ::= "(" "defmemory-agent" AgentName ":memory-store" PathString ":context-window-gc" Integer ")"
  ```
* **Core AST 展开映射**：自动配置 `MarkdownFS` 三层加载，并在超限时触发 `scoped-worker` 垃圾回收。

#### 13. 学习与适应 (Learning & Adaptation / SICA)
* **语法映射**：展开为带 `(:evolution ...)` 块的 AST，将进化目标限定为 `:skills` 目录。

#### 14. 探索与发现 (Exploration & Discovery)
* **语法映射**：注入“假设生成-实验执行-假说修正”三重轮次，并在 E2B 微型沙箱中隔离运行。

---

### 3.4 治理、安全与容错模式 (Governance, Safety & Fault-Tolerance)

#### 15. 异常处理与恢复 (Exception Handling & Recovery)
* **高层 EBNF 语法**：
  ```ebnf
  DefResilient ::= "(" "defresilient-agent" AgentName ":primary-tool" ToolId ":fallback-tool" ToolId ":max-retries" Integer ")"
  ```
* **Core AST 展开映射**：展开为 `:harness (:correct :max-retries retries :on-failure 'fallback-model)`。

#### 16. 人类参与环节 (Human-in-the-Loop, HITL)
* **高层 EBNF 语法**：
  ```ebnf
  DefApproval ::= "(" "defapproval-agent" AgentName ":sensitive-tools" "(" ToolId+ ")" ")"
  ```
* **Core AST 展开映射**：自动将 `:sensitive-tools` 写入 `:harness (:constrain :require-human-approval (tools...))`，在 Python 端自动触发 Temporal 挂起 Signal。

#### 17. 护栏与安全模式 (Guardrails & Safety)
* **高层 EBNF 语法**：
  ```ebnf
  DefGuarded ::= "(" "defguarded-agent" AgentName ":forbidden-commands" "(" String+ ")" ":workspace-root" PathString ")"
  ```
* **Core AST 展开映射**：直接填充 `:harness (:constrain ...)` 节点的安全路径与指令禁区。

#### 18. 评估与监控 (Evaluation & Monitoring)
* **语法映射**：在 `:harness (:verify ...)` 挂载 $\tau^2$-bench 验证与 OpenTelemetry OTLP 导出。

#### 19. 资源感知优化 (Resource-Aware Optimization)
* **语法映射**：展开为包含简单模型（Flash）与复杂模型（Pro）路由选择器的分支节点。

---

### 3.5 多智能体协作与目标模式 (Multi-Agent & Goal)

#### 20. 多智能体协作 (Multi-Agent Collaboration)
* **高层 EBNF 语法**：
  ```ebnf
  DefMultiAgent ::= "(" "defmultiagent" TeamName ":topology" TopologyType ":workers" "(" WorkerSpec+ ")" ")"
  ```
* **Core AST 展开映射**：展开为包含 `scoped-worker` 词法隔离节点的 `:multiagent` 节点。

#### 21. 目标设定与监控 (Goal Setting & Monitoring)
* **语法映射**：在 `:context` 中绑定 `:status-bar (:step-count #t :todo-list #t)`，并在每轮末尾附着 `<agent_status>` 标签。

---

## 4. Racket 编译器模块 (`compiler/patterns.rkt`) 实现与接线方案

Coding Agent 需创建 `compiler/patterns.rkt`，并使用 Racket 的 `define-syntax` 和 `syntax-case` 实现宏转换。

### 4.1 核心宏实现代码 (`compiler/patterns.rkt`)

```racket
#lang racket

;; =====================================================================
;; AgentLisp 模式宏扩展库 (compiler/patterns.rkt)
;; =====================================================================

(provide defreflect-agent
         defrouter-agent
         defworker-scoped)

;; 1. 反思模式宏展开器 (Reflection Pattern Macro)
(define-syntax (defreflect-agent stx)
  (syntax-case stx ()
    [(_ agent-name
        :provider provider-val
        :model-name model-val
        :tools (tool-id ...)
        :critic critic-prompt
        :max-retries retries-val)
     #'(defagent agent-name
         ;; 强制静态前缀 1: :model
         (:model :provider provider-val
                 :name model-val
                 :temperature 0.2
                 :system-prompt "你是一个具备自我反思能力的执行 Agent。")
         
         ;; 强制静态前缀 2: :tools
         (:tools (import-builtin tool-id ...)
                 (import-mcp "http://localhost:8000/mcp"))

         ;; 动态轨迹 3: :context
         (:context :memory-policy (:markdown-fs "./memory/reflection.md"
                                   :layers ('L0-Abstract 'L1-Overview)
                                   :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :current-branch #t :test-status #t))
         
         ;; 物理安全护栏 4: :harness
         (:harness
           (:constrain :require-human-approval ()
                       :forbidden-commands ("rm -rf" "dd" "mkfs"))
           (:verify :json-schema #t
                    :linter-check #t
                    :test-runner "pytest"
                    :reviewer-agent critic-prompt)
           (:correct :max-retries retries-val
                     :circuit-breaker 5
                     :on-failure 'fallback-model)))]))

;; 2. 路由模式宏展开器 (Router Pattern Macro)
(define-syntax (defrouter-agent stx)
  (syntax-case stx ()
    [(_ router-name
        :model (provider-val model-val)
        :routes ((:intent intent-tag => worker-id) ...))
     #'(defagent router-name
         (:model :provider provider-val
                 :name model-val
                 :temperature 0.0
                 :system-prompt "你是一个智能路由门控，负责分析用户意图并分发至正确 Worker。")
         (:tools (import-builtin bash))
         (:context :memory-policy (:markdown-fs "./memory/router.md" :layers ('L0-Abstract) :auto-append #f)
                   :skills ()
                   :status-bar (:step-count #t :current-branch #f :test-status #f))
         (:harness
           (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
           (:verify :json-schema #t :linter-check #f :test-runner "")
           (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))
         (:multiagent :topology 'orchestration
                      :workers ((scoped-worker worker-id
                                  (:model :provider provider-val :name model-val :temperature 0.2 :system-prompt "Worker")
                                  (:tools (import-builtin bash))
                                  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                            (:verify :json-schema #t :linter-check #f :test-runner "")
                                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))) ...)))]))

;; 3. 词法隔离 Worker 宏展开器 (Scoped Worker Macro)
(define-syntax (defworker-scoped stx)
  (syntax-case stx ()
    [(_ worker-name
        :tools (tool-id ...)
        :system-prompt sys-prompt)
     #'(scoped-worker worker-name
         (:model :provider "openai" :name "gpt-5.6" :temperature 0.0 :system-prompt sys-prompt)
         (:tools (import-builtin tool-id ...))
         (:harness
           (:constrain :require-human-approval () :forbidden-commands ("DROP DATABASE" "TRUNCATE" "rm -rf"))
           (:verify :json-schema #t :linter-check #f :test-runner "")
           (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))]))
```

### 4.2 编译器主入口接线 (`compiler/main.rkt`)
Coding Agent 需要在 `compiler/main.rkt` 中引入 `patterns.rkt`，并在 AST 解析前执行宏展开阶段：

```racket
#lang racket
(require "agentlisp_compiler.rkt"
         "patterns.rkt"
         (for-syntax "patterns.rkt"))

(provide compile-agentlisp-file)

(define (compile-agentlisp-file filepath)
  (let* ([raw-sexp (call-with-input-file filepath read)]
         ;; 1. Racket 宏展开阶段（Syntax Object）：将 Pattern Sugar 转化为 (defagent ...)
         [expanded-stx (expand (datum->syntax #f raw-sexp))]
         ;; 2. 脱壳为纯 S-exp（Syntax Object → list）
         [expanded-datum (syntax->datum expanded-stx)]
         ;; 3. 关键 BK-2 修复：若顶层宏展开产物为 (defagent NAME BLOCK…)，
         ;;    用 (define-agent NAME BLOCK…) 包装，精准命中 main.rkt L176 分支
         [top-form (match expanded-datum
                     [`(defagent ,name ,blocks ...)
                      `(define-agent ,name ,@blocks)]
                     [`,other-forms (cond
                                      [(list? other-forms) other-forms]
                                      [else (list other-forms)])])]
         ;; 4. 静态断言检查阶段 (KV 对齐与安全规约)
         [_ (check-ast-invariants top-form)]
         ;; 5. Python 目标代码转译阶段（复用现有 parse-defagent 路径，无新增依赖）
         [py-code (compile-agent-lisp top-form)])
    py-code))
```

> **接线说明（为什么这样写 = 零侵入现有 parser，无 BK-2 风险）**：
> - 实际 `compiler/main.rkt` 入口在 L176 `(define-agent name block…)` 处进行 pair? 匹配 → `parse-defagent` 手搓解析 5 块；宏展开器若直接返回 Syntax Object `#'(defagent …)` 则在 L176 不匹配，抛 top-level 错误；
> - 第 3 步显式用 `syntax->datum` 脱壳 + match 包装为 `define-agent`，保证输入到 parser 的顶层字节级形状与手写 `.al` 完全一致；
> - `(for-syntax "patterns.rkt")` 保证 patterns 中 21 宏在 compile-time 可见；
> - 对 `other-forms` fallback 保持兼容：若用户用原生 Core AST（无 Pattern Sugar）的 `define-agent` 顶层写法，直接 pass-through，不引入任何字节级差异。

---

## 5. 对接 Phase 3 双循环 RSI (递归自我进化) 的演进契约

当系统进入 Phase 3 双循环递归自我进化（RSI）时，模式宏层作为离线诊断器（Evolver）的核心变异目标：

### 5.1 声明式 DSL 语法扩展
在 AgentLisp 顶层语法中追加 `(:evolution ...)` 节点，允许离线 Evolver 自动调整模式与策略：

```lisp
(defreflect-agent code-repair-agent
  :provider "anthropic" :model-name "claude-3-7-sonnet"
  :tools (bash pytest) :critic "检查代码漏洞" :max-retries 3
  
  ;; 进化控制块
  (:evolution
    ;; 指定离线 Evolver 允许修改的突变目标
    (:mutation-targets :pattern-macros :skills :harness-retry)
    
    ;; 编译器静态死锁的不可变安全禁区 (绝不允许进化修改)
    (:immutable-invariants
      :kv-alignment                         ; 禁止破坏 Static Prefix 顺序
      :workspace-root                       ; 禁止逃逸沙箱路径锁
      :forbidden-commands)                  ; 禁止修改高危命令负面清单

    ;; τ²-bench 评估门控与卡方显著性断言
    (:verifier-gate "t2-bench@v1.0"
      :min-pass-rate 0.90
      :mcnemar-p-threshold 0.05)))
```

### 5.2 进化流程与静态安全断言
1. **在线只读 Trace**：`BaseHarnessV2` 运行过程中仅记录 `ExecutionTraceV2`，不直接改写自身代码。
2. **离线模式突变 (Pattern Mutation)**：`offline_evolver.py` 分析失败 Trace，自动将低效的普通 Agent 提升为 `defreflect-agent` 或 `defrouter-agent` 宏节点。
3. **编译期硬阻断**：若离线生成的宏展开后试图违反 `:immutable-invariants`（例如修改 `workspace-root`），`compiler/checker.rkt` 会立刻抛出 `ERR_UNGUARDED_TOOL_EXECUTION` 终止编译，阻断越权进化。

---

## 6. Coding Agent 交付验收标准与测试套件规范

Coding Agent 在完成 `compiler/patterns.rkt` 实现后，必须通过以下 3 层自动化测试方可交付：

### 6.1 单元测试套件 (`tests/test_patterns.rkt`)
编写 Racket 原生测试，验证所有 21 种模式宏能否无错误展开为合法的 AgentLisp AST：

```racket
#lang racket
(require rackunit
         "../compiler/patterns.rkt")

;; 测试 1: 验证 defreflect-agent 展开后的 AST 节点完整性
(check-true
 (match (expand '(defreflect-agent test-agent
                   :provider "openai" :model-name "gpt-5.6"
                   :tools (bash) :critic "test" :max-retries 3))
   [`(defagent test-agent (:model . ,_) (:tools . ,_) (:context . ,_) (:harness . ,_)) #t]
   [_ #f]))
```

### 6.2 静态断言集成测试 (`tests/test_pattern_checker.py`)
使用 Python 测试脚本验证宏展开后的代码能够通过 `ERR_KV_ALIGNMENT_VIOLATION` 校验：

```python
import pytest
from compiler.transpiler import compile_pattern_sugar


def test_pattern_macro_kv_alignment():
    sugar_code = """
    (defreflect-agent auto-agent
      :provider "anthropic" :model-name "claude-3-7-sonnet"
      :tools (bash) :critic "check" :max-retries 3)
    """
    py_code = compile_pattern_sugar(sugar_code)
    # 断言编译产物包含 KV 静态前缀对齐代码
    assert "self.model_config =" in py_code
    assert "self.harness_config =" in py_code
```

### 6.3 验收交付 CheckList
* [ ] `compiler/patterns.rkt` 完整实现并导出 21 种设计模式宏。
* [ ] 所有模式宏展开后的 AST 100% 包含 `:model` 和 `:tools` 静态前缀。
* [ ] 编译测试用例 `pytest tests/test_patterns.py` 达到 100% Pass。
* [ ] 运行 `ruff check` 与 `ruff format` 达到无错误诊断（0 diagnostics）。
