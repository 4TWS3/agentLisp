;; defchain-agent doc-pipeline → Core AST 展开期望
;; SBE 推导依据：Pattern Spec §3.1 L66-L78 "将步骤依赖链写入 system prompt，并在 :harness 中注入多步顺序断言"
(defagent doc-pipeline
  (:model :provider "anthropic"
          :name "claude-3-7-sonnet"
          :temperature 0.0
          :system-prompt #<<PROMPT
你是一个多步骤提示链（Prompt Chaining）执行 Agent。必须严格按以下给定顺序执行步骤，不得跳过或打乱：
Step 1 — 提取文档摘要 :in () :out summary
  Prompt: "提取文档摘要"
Step 2 — 基于摘要生成代码 :in (summary) :out code
  Prompt: "基于摘要生成代码"
每一步完成后，把 :out 变量注入到后续 :in 步骤的上下文中；最终 Answer 必须包含 JSON {"summary": … "code": …}。
PROMPT
          )
  (:tools (import-builtin bash pytest))
  (:context :memory-policy (:markdown-fs "./memory/doc-pipeline.md"
                            :layers ('L0-Abstract 'L1-Overview)
                            :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :current-branch #t :test-status #t))
  (:harness
    (:constrain :require-human-approval ()
                :forbidden-commands ("rm -rf"))
    (:verify :json-schema #t
             :linter-check #f
             :test-runner ""
             ;; 顺序断言：保证 Step1 在 Step2 之前完成（链不能并行）
             :step-order-assertion ("Step1 summary MUST appear in trajectory before Step2 code request"))
    (:correct :max-retries 2 :circuit-breaker 5 :on-failure 'abort)))
