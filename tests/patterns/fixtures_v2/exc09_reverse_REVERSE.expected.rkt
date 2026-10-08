;; exc09_reverse (reverse) 宏展开期望 — CR-41 defexception
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent exc09_reverse
  (:model :provider "azure-openai"
          :name "gpt-5.6"
          :temperature 0.0
          :system-prompt "CR-41 V2 defexception agent exc09_reverse: 使用给定 defexception 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash python-repl))
  (:context :memory-policy (sqlite-table "./rev.db" :table "exc09_reverse" :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands ("poweroff" "format") :human-approval (all)))
    (:verify (:json-schema #t :linter-check mypy :test-runner "tox -e py312"))
    (:correct (:max-retries 5 :circuit-breaker 3 :on-failure dlq)))
  (:multiagent
    (:pattern-kind defexception)
    (:pattern-config
              (monitoring stdout)
              (dead-letter /dev/null)
              (retry-policy (none))
              (fallback raise))))
