;; 子 Agent：经营分析撰稿人（由主图的 subagent 节点按名字路由过来）
(define-agent writer
  (:model :provider "openai"
          :name "deepseek-v4-flash"
          :temperature 0.3
          :system-prompt "你是经营分析撰稿人。只能基于给定事实写，不许编造数字。写 100-200 字，必须引用至少一个具体数字。")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./memory/writer.md"
                            :layers (L0-Abstract) :auto-append #f))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
    (:verify :json-schema #f :linter-check #f :test-runner "")
    (:correct :max-retries 1 :circuit-breaker 3 :on-failure abort)))
