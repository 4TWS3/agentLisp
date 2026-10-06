;; =====================================================================
;; defreflect-agent code-refiner → Core AST 展开期望（字节级全等）
;; SBE fixtures 来源：docs/agentlisp-pattern-macros-tech-spec.md §4.1 L254-L291
;; 注：顶层形式为 (defagent NAME BLOCK…)，后续 main.rkt 宏展开 pass 会再包一层
;;     (define-agent NAME BLOCK…) 以命中 parse-defagent 分支
;; =====================================================================
(defagent code-refiner
  (:model :provider "anthropic"
          :name "claude-3-7-sonnet"
          :temperature 0.2
          :system-prompt "你是一个具备自我反思能力的执行 Agent。")
  (:tools (import-builtin bash pytest)
          (import-mcp "http://localhost:8000/mcp"))
  (:context :memory-policy (:markdown-fs "./memory/reflection.md"
                            :layers ('L0-Abstract 'L1-Overview)
                            :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :current-branch #t :test-status #t))
  (:harness
    (:constrain :require-human-approval ()
                :forbidden-commands ("rm -rf" "dd" "mkfs"))
    (:verify :json-schema #t
             :linter-check #t
             :test-runner "pytest"
             :reviewer-agent "检查代码逻辑漏洞")
    (:correct :max-retries 3
              :circuit-breaker 5
              :on-failure 'fallback-model)))
