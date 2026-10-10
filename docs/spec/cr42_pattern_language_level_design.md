# CR-42 设计：21 个设计模式落到 DSL 语言层

> 状态：设计提案（待 Owner 批准后实施）· 2026-10-11
> 依据：CR-41 独立审计 finding「语法层 0/21、宏层 15/21、语义只活在 system-prompt」
> 目标：让模式成为**可静态校验**的语言构造，而不是提示词约定。

## 1. 结论

现状：模式只到宏层。语法层 0 个。

方案：加**一个**可扩展构造 `:pattern`，配**模式注册表**。

效果：新增模式只改注册表，不改四个核心文件。

## 2. 现状（可复核）

| 层次 | 数量 | 证据 |
|---|---:|---|
| Core AST 专属语法 | 0 / 21 | 白名单无模式键；`:pattern-kind` 等非法 |
| 宏层（syntax-case） | 15 / 21 | V1 5 宏 + V2 10 宏 |
| 仅提示词文本 | 多数 | 语义写在 `:system-prompt` |
| spec 引用但语法不存在 | ≥3 | `:evolution`、模型路由分支、A2A 头 |

后果：模式语义无法静态断言。审计给 AC-1 = 3 分。

## 3. 设计：单一构造 + 注册表

### 3.1 语法（唯一新增）

    (:pattern (:kind priority)
              (:config (:criteria "...") (:levels 3))
              (:rule "高优先级先执行"))

要点：

- 只加 `:pattern` 一个块，不加 21 个键。
- `:kind` 取值来自注册表，不是硬编码枚举。
- `:config` 由各模式自己的 schema 校验。

### 3.2 注册表（数据驱动）

    ;; compiler/pattern_registry.rkt（新文件，非 C1）
    (define-registry-entry
      #:kind 'priority
      #:schema (hash 'criteria 'string? 'levels 'positive-integer?)
      #:required-keys '(criteria)
      #:emit (lambda (cfg) ...))   ; 生成 Python 侧真实结构

要点：

- 一条 entry = 一个模式。加模式 = 加一条数据。
- parser / checker / emitter 只查表，不写分支。

### 3.3 三处核心改动点（C1，需批准）

| 文件 | 改动 | 规模 |
|---|---|---|
| agentlisp_compiler.rkt | 白名单加 `:pattern`；新增 parse-pattern 查表校验 | 约 40 行 |
| checker.rkt | 模式 config 的 schema 校验与错误码 | 约 30 行 |
| emitter.rkt | 调用注册表 `:emit` 生成运行时结构 | 约 20 行 |

parser.rkt 不动。枚举表不动（`:kind` 不再硬编码）。

## 4. 迁移路线（四阶段）

| 阶段 | 内容 | 判定 |
|---|---|---|
| P-1 | 注册表骨架 + `:pattern` 语法 + priority 一个模式 | 该模式可静态断言 |
| P-2 | V2 十宏改产 `:pattern` | 30 契约夹具重生成 |
| P-3 | V1 五宏迁移 + 补齐剩余 6 模式 | 21/21 覆盖 |
| P-4 | 关掉 prompt-only 语义路径 | 标记断言取代文本断言 |

每阶段都必须过：AST 闸门、端到端编译测试、标记独立断言。

## 5. 风险与对策

| 风险 | 对策 |
|---|---|
| 语法再次封闭（21 键） | 只加 `:pattern`；kind 走注册表 |
| 核心文件改动失控 | 三处改动合计 ≤ 90 行，逐处 review |
| 迁移期双轨 | 宏继续可用；新语法与旧宏并存一个 CR |
| 契约夹具漂移 | 夹具由注册表生成器统一产出 |

## 6. 验收判据

1. `:pattern` 之外无新增顶层键（grep 白名单）。
2. 21 个 kind 全部在注册表内，且各有 schema。
3. 非法 config 必须编译期报错（负向用例 >= 21）。
4. 标记断言全部来自 AST，不来自 prompt 文本。
5. C1 三文件改动合计 <= 90 行，且每行有注释。

## 7. 不做的事

- 不为每个模式加专属键。
- 不把 21 个模式塞进枚举。
- 不在本轮改 workflow 或发布链路。
