;; topic05_generic (generic) 宏展开期望 — CR-41 deftopic-model
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent topic05_generic
  (:model :provider "anthropic"
          :name "claude-3-5-sonnet"
          :temperature 0.5
          :system-prompt "CR-41 V2 deftopic-model agent topic05_generic: 使用给定 deftopic-model 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash))
  (:context :memory-policy (markdown-fs "/tmp/g/topic05_generic.md" :layers (L0) :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands () :human-approval ()))
    (:verify (:json-schema #f :linter-check "" :test-runner ""))
    (:correct (:max-retries 1 :circuit-breaker 1000 :on-failure abort)))
  (:multiagent
    (:pattern-kind deftopic-model)
    (:pattern-config
              (threshold 0.55)
              (taxonomy flat)
              (clustering dbscan)
              (topics (a b c)))))
