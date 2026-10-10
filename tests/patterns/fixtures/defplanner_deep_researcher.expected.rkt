;; defplanner-agent deep-researcher → Core AST 展开期望
;; SBE 依据：Pattern Spec §3.1 L108-L120 "在 :model 注入 CoT 计划生成 Prompt"
;; 合法化修订（P0-4）：原 :harness :verify 下的 :plan-completion-assertion 不在白名单内，
;; 断言语义已并入 system-prompt，仅使用白名单键。
(defagent deep-researcher
  (:model :provider "anthropic"
          :name "claude-3-7-sonnet"
          :temperature 0.7
          :system-prompt #<<PROMPT
你是一个具备规划能力（Planning）的 Agent。
Planner Prompt："将研究目标分解为 3-5 个步骤"
执行流程：
  Step P1 — 在 trajectory 首部输出计划 JSON {"plan": ("步骤1", "步骤2", "步骤3", …)}，步骤数必须 ∈ (3, 5)
  Step P2…Pn — 按计划逐步执行，仅可使用 executor-tools: web-search / read-pdf
  Step FIN — 输出计划完成度报告 {"plan_total": N, "plan_done": M, "unfinished": (…)}
计划断言：计划步骤数必须 ∈ (3, 5)；FIN 阶段的 unfinished 列表必须为空。
PROMPT
          )
  (:tools (import-builtin web-search read-pdf))
  (:context :memory-policy (:markdown-fs "./memory/deep-researcher.md"
                            :layers ('L0-Abstract 'L1-Overview)
                            :auto-append #t)
            :skills ()
            :status-bar (:step-count #t :current-branch #t :test-status #t :todo-list #t))
  (:harness
    (:constrain :require-human-approval (web-search read-pdf)
                :forbidden-commands ("rm -rf"))
    (:verify :json-schema #t
             :linter-check #f
             :test-runner "")
    (:correct :max-retries 3 :circuit-breaker 5 :on-failure 'ask-human)))
