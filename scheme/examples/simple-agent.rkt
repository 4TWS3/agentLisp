#lang racket/base

(require "../agent-dsl/main.rkt")

(define-tool search-document
  #:description "按关键词搜索文档库"
  #:input '#hash((query . string?) (limit . number?))
  #:output '#hash((results . list?)))

(define-tool generate-report
  #:description "根据数据生成格式化报告"
  #:input '#hash((data . any/c) (template . string?))
  #:output '#hash((report . string?) (path . string?)))

(define-tool validate-compliance
  #:description "校验文档合规性"
  #:input '#hash((document . string?) (rules . list?))
  #:output '#hash((pass . boolean?) (issues . list?)))

(define-tool notify-user
  #:description "向用户发送通知"
  #:input '#hash((channel . string?) (message . string?))
  #:output '#hash((sent . boolean?)))

;; 顺序说明：Racket 要求先定义后引用，而 #:next 指向下一个步骤，
;; 因此这里按依赖倒序定义；工作流的 #:steps 仍按正向执行顺序书写（见下方）。
(define-step notify-result
  (atomic send-message notify channel "email" "处理完成"))

(define-step generate-output
  (atomic create-report generate data "results" "标准模板")
  #:next notify-result)

(define-step check-rules
  ;; rules 不是绑定标识符，规则清单直接作为列表传入
  (atomic verify compliance document "项目书.docx" (list "rule-1" "rule-2" "rule-3"))
  ;; define-step 的关键字顺序固定为 #:next 之后 #:when
  #:next generate-output
  #:when #t)

(define-step collect-info
  ;; atomic 的 params 是表达式列表，不能写未绑定的 limit；限制值直接作为参数传入
  (atomic search-docs knowledge query "项目申报书" 50)
  #:next check-rules)
(define-workflow document-review
  #:triggers '(manual schedule)
  #:steps (collect-info check-rules generate-output notify-result))

(define-workflow scheduled-audit
  #:triggers '(schedule)
  #:steps (collect-info check-rules))

(define-agent compliance-reviewer
  #:purpose "政务项目申报书合规性审查 Agent"
  #:tools (search-document generate-report validate-compliance notify-user)
  #:workflows (document-review scheduled-audit))

(module+ main
  (require "../agent-dsl/reader.rkt")
  (printf "Agent: ~a~n" (agent-name compliance-reviewer))
  (printf "Purpose: ~a~n" (agent-purpose compliance-reviewer))
  (printf "Tools: ~a~n" (map tool-name (agent-tools compliance-reviewer)))
  (printf "Workflows: ~a~n" (map workflow-name (agent-workflows compliance-reviewer)))
  (define-values (valid? msg) (validate-agent compliance-reviewer))
  (printf "Validation: ~a - ~a~n" valid? msg)
  (printf "~nJSON Output:~n~a~n" (agent-to-json compliance-reviewer)))
