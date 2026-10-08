;; hitl08_generic (generic) 宏展开期望 — CR-41 defhitl
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent hitl08_generic
  (:model :provider "anthropic"
          :name "claude-3-5-sonnet"
          :temperature 0.5
          :system-prompt "CR-41 V2 defhitl agent hitl08_generic: 使用给定 defhitl 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash))
  (:context :memory-policy (markdown-fs "/tmp/g/hitl08_generic.md" :layers (L0) :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands () :human-approval ()))
    (:verify (:json-schema #f :linter-check "" :test-runner ""))
    (:correct (:max-retries 1 :circuit-breaker 1000 :on-failure abort)))
  (:multiagent
    (:pattern-kind defhitl)
    (:pattern-config
              (timeout 1h)
              (approval-policy (any-cost>50))
              (audit-log local)
              (escalation email))))
