;; priority01_reverse (reverse) 宏展开期望 — CR-41 defpriority
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent priority01_reverse
  (:model :provider "azure-openai"
          :name "gpt-5.6"
          :temperature 0.0
          :system-prompt "CR-41 V2 defpriority agent priority01_reverse: 使用给定 defpriority 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash python-repl))
  (:context :memory-policy (sqlite-table "./rev.db" :table "priority01_reverse" :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands ("poweroff" "format") :human-approval (all)))
    (:verify (:json-schema #t :linter-check mypy :test-runner "tox -e py312"))
    (:correct (:max-retries 5 :circuit-breaker 3 :on-failure dlq)))
  (:multiagent
    (:pattern-kind defpriority)
    (:pattern-config
              (routing-table ((a => b)))
              (policies ((x 1)))
              (priority-level 1))))
