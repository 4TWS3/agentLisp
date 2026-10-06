;; defrouter-agent ops-gateway → Core AST 展开期望（SBE fixtures · §4.1 L293-L318）
(defagent ops-gateway
  (:model :provider "openai"
          :name "gpt-5.6"
          :temperature 0.0
          :system-prompt "你是一个智能路由门控，负责分析用户意图并分发至正确 Worker。")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./memory/router.md"
                            :layers ('L0-Abstract)
                            :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :current-branch #f :test-status #f))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
    (:verify :json-schema #t :linter-check #f :test-runner "")
    (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))
  (:multiagent :topology 'orchestration
               :workers ((scoped-worker db-worker
                           (:model :provider "openai" :name "gpt-5.6" :temperature 0.2 :system-prompt "Worker")
                           (:tools (import-builtin bash))
                           (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                     (:verify :json-schema #t :linter-check #f :test-runner "")
                                     (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))
                          (scoped-worker net-worker
                           (:model :provider "openai" :name "gpt-5.6" :temperature 0.2 :system-prompt "Worker")
                           (:tools (import-builtin bash))
                           (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                     (:verify :json-schema #t :linter-check #f :test-runner "")
                                     (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))))))
