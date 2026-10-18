;; 第一个示例：命令行助手（真的会调 bash）
;;
;; 用法：
;;   racket compiler/main.rkt -i examples/first-agent.al -o examples/dist/first_agent.py
;;   python examples/first_agent_run.py

(define-agent first-agent
  (:model :provider "openai"
          :name "qwen3:4b"
          :temperature 0.1
          :system-prompt "你是命令行助手。需要事实时必须调用 bash 工具，不要凭空回答。统计文件数量时用递归命令（如 find . -name '*.py' | wc -l），不要只数当前层。回答用中文，一句话。")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./memory/first-agent.md"
                            :layers (L0-Abstract)
                            :auto-append #f))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf" "sudo"))
    (:verify :json-schema #t :linter-check #f :test-runner "")
    (:correct :max-retries 1 :circuit-breaker 3 :on-failure abort)))
