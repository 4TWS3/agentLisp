;; defchain-agent doc-pipeline → Core AST 展开期望
;; SBE 推导依据：Pattern Spec §3.1 L66-L78 "将步骤依赖链写入 system prompt"
;; 合法化修订（P0-4）：原 :harness :verify 下的 :step-order-assertion 不在 parser 白名单内，
;; 会把产物编译拦死；断言语义已并入 system-prompt，仅使用白名单键。
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
顺序断言：Step1 的 summary 必须出现在 Step2 的代码请求之前（trajectory 时间顺序）。
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
             :test-runner "")
    (:correct :max-retries 2 :circuit-breaker 5 :on-failure 'abort)))
