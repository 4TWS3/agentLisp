;; tianji 切片：5 节点流水线（与 tianji 真实图同形）
;;   facts(computation) -> value_judge -> operator_eval -> improve -> report
;;
;; 图由 agentLisp 声明，执行交给 LangGraph（runtime/langgraph_bridge.py）。
(define-agent tianji-slice
  (:model :provider "openai"
          :name "deepseek-v4-flash"
          :temperature 0.2
          :system-prompt "你是经营研判分析师。结论只能基于给你的确定性事实，不得编造数字。")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./memory/tianji-slice.md"
                            :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((value_judgment :type str)
                   (operator_evaluation :type str)
                   (improvement_plan :type str)
                   (report :type str)))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
    (:verify :json-schema #f :linter-check #f :test-runner "")
    (:correct :max-retries 2 :circuit-breaker 3 :on-failure abort))
  (:workflow :entry facts
    :nodes ((facts :type computation :handler "examples.tianji_slice.metrics.compute")
            (value_judge :type agent :output-fields (value_judgment))
            (operator_eval :type agent :output-fields (operator_evaluation))
            (improve :type agent :output-fields (improvement_plan))
            (report :type agent :output-fields (report)))
    :topology ((edge facts value_judge)
               (edge value_judge operator_eval)
               (edge operator_eval improve)
               (edge improve report))))
