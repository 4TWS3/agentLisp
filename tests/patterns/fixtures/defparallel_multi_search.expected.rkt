;; defparallel-agent multi-search → Core AST 展开期望
;; SBE 依据：Pattern Spec §3.1 L95-L106 "展开为 multiagent 并发节点，多个 scoped-worker 并行，最终 aggregator-agent 归并"
(defagent multi-search
  (:model :provider "anthropic"
          :name "claude-3-7-sonnet"
          :temperature 0.0
          :system-prompt "你是一个并行分支协调器（Parallelization Coordinator）。所有 :branches 下的 Worker 将被同时拉起，不得串行；全部结束后将各 Worker 结果交给 :reducer aggregator-agent 归并。并行断言：search-a 与 search-b 的轮次允许在 trajectory 时间线上交错。")
  (:tools (import-builtin bash read-pdf))
  (:context :memory-policy (:markdown-fs "./memory/multi-search.md"
                            :layers ('L0-Abstract)
                            :auto-append #f)
            :skills ()
            :status-bar (:step-count #t :current-branch #f :test-status #t))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
    (:verify :json-schema #t
             :linter-check #f
             :test-runner ""
    (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))
  (:multiagent :topology 'orchestration
               :workers ((scoped-worker search-a
                           (:model :provider "anthropic" :name "claude-3-7-sonnet" :temperature 0.2 :system-prompt "来源 A 的检索 Worker")
                           (:tools (import-builtin bash read-pdf))
                           (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                     (:verify :json-schema #t :linter-check #f :test-runner "")
                                     (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))
                          (scoped-worker search-b
                           (:model :provider "anthropic" :name "claude-3-7-sonnet" :temperature 0.2 :system-prompt "来源 B 的检索 Worker")
                           (:tools (import-builtin bash read-pdf))
                           (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                     (:verify :json-schema #t :linter-check #f :test-runner "")
                                     (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))
                          (scoped-worker aggregator-agent
                           (:model :provider "anthropic" :name "claude-3-7-sonnet" :temperature 0.2 :system-prompt "Reducer：将 search-a、search-b 的结果合并为最终 JSON 输出，不得重复内容")
                           (:tools (import-builtin bash))
                           (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                     (:verify :json-schema #t :linter-check #f :test-runner "")
                                     (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))))))
