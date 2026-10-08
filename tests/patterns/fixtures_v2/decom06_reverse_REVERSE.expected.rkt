;; decom06_reverse (reverse) 宏展开期望 — CR-41 defdecomposer
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent decom06_reverse
  (:model :provider "azure-openai"
          :name "gpt-5.6"
          :temperature 0.0
          :system-prompt "CR-41 V2 defdecomposer agent decom06_reverse: 使用给定 defdecomposer 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash python-repl))
  (:context :memory-policy (sqlite-table "./rev.db" :table "decom06_reverse" :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands ("poweroff" "format") :human-approval (all)))
    (:verify (:json-schema #t :linter-check mypy :test-runner "tox -e py312"))
    (:correct (:max-retries 5 :circuit-breaker 3 :on-failure dlq)))
  (:multiagent
    (:pattern-kind defdecomposer)
    (:pattern-config
              (merge first)
              (techniques (llm))
              (granularity token-512)
              (subagent-pool (solo)))))
