;; AgentLisp v2.0 最小示例：文档修复 Agent（对齐当前 Core AST 语法）
;; ----------------------------------------------------------
;; 用法：
;;   racket compiler/main.rkt -i examples/repair_agent.al -o examples/dist/repair_agent.py
;;
;; 语法说明（2026-10-11 改写）：
;;   本文件此前使用 define-tool / define-harness / define-workflow / define-step 等构造。
;;   这些构造尚未进入 Core AST 白名单（属 CR-42「模式与工作流落语言层」议题），
;;   因此当前无法编译。现改写为可编译形式：
;;     - 工具：走 :tools 白名单键（import-builtin / import-mcp / define-tool 数据块）；
;;     - 流程语义：写入 :model :system-prompt（与 15 个模式宏同一口径）。

(define-agent document-repairer
  (:model :provider "anthropic"
          :name "claude-3-7-sonnet"
          :temperature 0.2
          :system-prompt "你按 DCAF L0/L1/L2 规则修复政务文档。流程固定为三步：s1-read 读取 input/doc.md；s2-patch 对「项目背景」小节打补丁；s3-write 写回并保留版本记录。每一步的结果必须注入下一步上下文；写回前必须获得人工批准。")
  (:tools (import-builtin bash read-file patch-text write-back))
  (:context :memory-policy (:markdown-fs "./memory/document-repairer.md"
                            :layers (L0-Abstract L1-Overview L2-FullText)
                            :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :current-branch #t :test-status #t))
  (:harness
    (:constrain :require-human-approval (write-back)
                :forbidden-commands ("rm -rf"))
    (:verify :json-schema #t
             :linter-check #t
             :test-runner "pytest tests/")
    (:correct :max-retries 3 :circuit-breaker 5 :on-failure fallback-model)))
