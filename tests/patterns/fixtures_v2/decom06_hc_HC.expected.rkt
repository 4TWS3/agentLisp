;; decom06_hc (hc) 宏展开期望 — CR-41 defdecomposer
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent decom06_hc
  (:model :provider "openai"
          :name "gpt-5.6"
          :temperature 0.2
          :system-prompt "CR-41 V2 defdecomposer agent decom06_hc: 使用给定 defdecomposer 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (web-search python-repl read-pdf))
  (:context :memory-policy (markdown-fs "./memory/decom06_hc.md" :layers (L0 L1) :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
    (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
    (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
  (:multiagent
    (:pattern-kind defdecomposer)
    (:pattern-config
              (granularity per-paragraph)
              (techniques (mdp-splitting llm-judged heuristic))
              (subagent-pool (worker-a worker-b worker-c))
              (merge weighted-vote))))
