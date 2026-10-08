;; explore10_hc (hc) 宏展开期望 — CR-41 defexploration
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent explore10_hc
  (:model :provider "openai"
          :name "gpt-5.6"
          :temperature 0.2
          :system-prompt "CR-41 V2 defexploration agent explore10_hc: 使用给定 defexploration 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (web-search python-repl read-pdf))
  (:context :memory-policy (markdown-fs "./memory/explore10_hc.md" :layers (L0 L1) :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
    (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
    (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
  (:multiagent
    (:pattern-kind defexploration)
    (:pattern-config
              (search-space (hyperparam-range lr [1e-5 1e-2] batch [32 512]))
              (budget (max-trials 200 max-time 2h wall))
              (pruning (median-stop 5%-ile after 5 trials))
              (rollout (ucb-exploration c=2.0)))))
