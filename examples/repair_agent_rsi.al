;; RSI 示例（规格 §3.3 的可编译版）：声明进化契约。
;;
;; 用法：
;;   racket compiler/main.rkt -i examples/repair_agent_rsi.al -o examples/dist/repair_agent_rsi.py
;;
;; 关键点：
;;   - :mutation-targets 只能在这些目标里改；越界编译期拒绝
;;   - :immutable-invariants 是禁区；把禁区写进 targets 会抛 ERR_IMMUTABLE_INVARIANT_VIOLATION

(define-agent production-repair-agent-rsi
  (:model :provider "openai"
          :name "gpt-4o"
          :temperature 0.2
          :system-prompt "你是一个严谨的代码修复 Agent。先读记忆，再隔离修改，最后跑 pytest 校验。")
  (:tools (import-builtin read-file bash apply-patch-builtin))
  (:context :memory-policy (:markdown-fs "./workspace"
                            :layers (L0-Abstract L1-Overview L2-FullText)
                            :auto-append #t))
  (:harness
    (:constrain :forbidden-commands ("rm -rf /" "git reset --hard")
                :require-human-approval (git-push)
                :workspace-root "./workspace")
    (:verify :json-schema #t :linter-check #t :test-runner "pytest tests/")
    (:correct :max-retries 3 :circuit-breaker 5 :on-failure abort))
  (:evolution :online-trace #t
              :offline-evolver "meta-diagnosis-agent"
              :mutation-targets (skills prompt-patches harness-retry pattern-macros)
              :immutable-invariants (kv-alignment workspace-root forbidden-commands)
              :verifier-gate (:suite "t2-bench@v1.0"
                             :min-pass-rate 0.90
                             :mcnemar-p-threshold 0.05)))
