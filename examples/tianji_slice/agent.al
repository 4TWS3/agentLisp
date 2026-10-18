;; tianji 切片（全能力验证）：确定性事实 + 子 Agent + 图级重试 + 状态累积
;;
;; facts(computation) -> draft(subagent: writer) -> review(evaluator)
;;   ↑__________________ conditional-loop（评审不过就重写）__________________|
;;   review -> report(agent)
;;
;; 用到的 agentLisp 能力：
;;   :workflow 节点图 / :handler / subagent 按名路由 / conditional-loop / :state :reducer
(define-agent tianji-slice
  (:model :provider "openai"
          :name "deepseek-v4-flash"
          :temperature 0.2
          :system-prompt "你是经营研判分析师。结论只能基于给定的确定性事实，不得编造数字。")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./memory/tianji-slice.md"
                            :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((facts :type dict)
                   (draft :type str)
                   (sections :type list :reducer append :default ())
                   (review_ok :type bool :default #f)
                   (review_reason :type str)
                   (report :type str)))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
    (:verify :json-schema #f :linter-check #f :test-runner "")
    (:correct :max-retries 2 :circuit-breaker 3 :on-failure abort))
  (:workflow :entry facts
    :nodes ((facts :type computation :handler "examples.tianji_slice.metrics.facts"
                   :output-fields (facts))
            (draft :type subagent :handler "writer"
                   :prompt (:static "根据下面的确定性事实，写一段 100-200 字的经营研判（必须引用具体数字）。"
                            :dynamic "事实：{facts}")
                   :output-fields (draft))
            (review :type evaluator :handler "examples.tianji_slice.review.review"
                    :output-fields (review_ok review_reason sections))
            (report :type agent
                    :prompt (:static "把评审通过的草稿压缩成一句话结论。")
                    :output-fields (report)))
    :topology ((edge facts draft)
               (edge draft review)
               (conditional-loop :nodes (draft review) :while "retry" :max-rounds 3)
               (edge review report))))
