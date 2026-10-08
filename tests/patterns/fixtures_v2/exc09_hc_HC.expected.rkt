;; exc09_hc (hc) 宏展开期望 — CR-41 defexception
;; 5 桶升序: :model(0) → :tools(1) → :context(2) → :harness(3) → :multiagent(4)
(define-agent exc09_hc
  (:model :provider "openai"
          :name "gpt-5.6"
          :temperature 0.2
          :system-prompt "CR-41 V2 defexception agent exc09_hc: 使用给定 defexception 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
  (:tools (web-search python-repl read-pdf))
  (:context :memory-policy (markdown-fs "./memory/exc09_hc.md" :layers (L0 L1) :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :cost #t :latency-p95 #t))
  (:harness
    (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
    (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
    (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
  (:multiagent
    (:pattern-kind defexception)
    (:pattern-config
              (fallback (degrade-to-cache retry-best-effort))
              (retry-policy (exponential-backoff base 2s max 10))
              (dead-letter (s3 bucket + dlq-notify))
              (monitoring (datadog alarm-threshold 5/5min)))))
