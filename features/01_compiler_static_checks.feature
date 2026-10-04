# language: zh-CN
功能: AgentLisp v2.0 编译器静态检查规约 (FR-CHECK)
  作为 AgentLisp 编译架构师
  我需要编译器在语法分析与 AST 构建阶段执行 3 大硬性不可变规约校验
  以在编译期阻断 KV Cache 破坏、裸工具调用和作用域冲突

  背景:
    假如 启动 AgentLisp Racket 编译器前端 (compiler/main.rkt)
    并且 开启静态断言检查选项 (--check-only)

  @FR-CHECK-1 @KV-Alignment
  场景大纲: KV Cache 静态前缀强对齐校验 (ERR_KV_ALIGNMENT_VIOLATION)
    假如 DSL 源码中包含声明块 "<first_block>" 与 "<second_block>"
    当 编译器解析 AST 并校验块顺序
    那么 编译校验结果应当为 "<status>"
    并且 返回的标准错误码应当为 "<error_code>"

    例子:
      | first_block              | second_block            | status  | error_code                 |
      | (:model "claude-3-5")    | (:context :auto)        | PASS    | NONE                       |
      | (:tools [bash])          | (:context :auto)        | PASS    | NONE                       |
      | (:context :auto)         | (:model "claude-3-5")   | FAIL    | ERR_KV_ALIGNMENT_VIOLATION |
      | (:context :auto)         | (:tools [bash])         | FAIL    | ERR_KV_ALIGNMENT_VIOLATION |

  @FR-CHECK-2 @Unguarded-Tool
  场景: 声明具副作用工具但缺少 Harness 护栏 (ERR_UNGUARDED_TOOL_EXECUTION)
    假如 DSL 源码中声明了具副作用本地工具 "bash"
    但是 该工具配置中没有声明 ":harness" 门控且没有 ":require-approval" 标注
    当 编译器执行 AST 静态校验
    那么 编译器应当拒绝代码生成
    并且 抛出错误码 "ERR_UNGUARDED_TOOL_EXECUTION"
    并且 抛出修复提示 "Hints: Add :harness or :require-approval for side-effect tools"

  @FR-CHECK-3 @Tool-Name-Collision
  场景: 跨 Agent 作用域工具命名冲突校验 (ERR_CONTEXT_LEAKAGE)
    假如 主 Agent 声明了工具 "file_editor"
    并且 子 Agent "worker_a" 再次声明了同名工具 "file_editor"
    当 编译器解析全局作用域语法树
    那么 编译器应当抛出错误码 "ERR_CONTEXT_LEAKAGE"

  @SRS-5.1 @JSON-Errors
  场景: CLI 导出精准 srcloc JSON 错误格式
    假如 带有语序错误的源码 "repair_agent.al" 触发了 "ERR_KV_ALIGNMENT_VIOLATION"
    当 运行命令 "racket compiler/main.rkt repair_agent.al --json-errors"
    那么 标准输出流 (stdout) 输出应为标准的 JSON 数组格式
    并且 JSON 对象中应精准包含 "code", "srs_id", "srcloc.line", "srcloc.column" 及 "hints" 字段
