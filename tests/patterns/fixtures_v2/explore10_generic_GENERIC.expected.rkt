;; explore10_generic (generic) 宏展开期望 — CR-41 defexploration
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent explore10_generic
  (:model :provider "anthropic"
          :name "claude-3-5-sonnet"
          :temperature 0.5
          :system-prompt "CR-41 V2 defexploration agent explore10_generic: 使用给定 defexploration 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (bash))
  (:context :memory-policy (markdown-fs "/tmp/g/explore10_generic.md" :layers (L0) :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands () :human-approval ()))
    (:verify (:json-schema #f :linter-check "" :test-runner ""))
    (:correct (:max-retries 1 :circuit-breaker 1000 :on-failure abort)))
  (:multiagent
    (:pattern-kind defexploration)
    (:pattern-config
              (budget (max-trials 20))
              (search-space (depth 1..10))
              (rollout (epsilon-greedy eps=0.1))
              (pruning none))))
