;; guard07_generic (generic) 宏展开期望 — CR-41 defguardrails-safety
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent guard07_generic
  (:model :provider "anthropic"
          :name "claude-3-5-sonnet"
          :temperature 0.5
          :system-prompt "CR-41 V2 defguardrails-safety agent guard07_generic: 使用给定 defguardrails-safety 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash))
  (:context :memory-policy (markdown-fs "/tmp/g/guard07_generic.md" :layers (L0) :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands () :human-approval ()))
    (:verify (:json-schema #f :linter-check "" :test-runner ""))
    (:correct (:max-retries 1 :circuit-breaker 1000 :on-failure abort)))
  (:multiagent
    (:pattern-kind defguardrails-safety)
    (:pattern-config
              (audit (sampled 10%))
              (escalation (auto-block))
              (input-policy (pii-only))
              (output-policy (basic)))))
