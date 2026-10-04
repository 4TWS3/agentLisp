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

(define-step collect-info
  (atomic search-docs knowledge query "项目申报书" limit 50)
  #:next check-rules)

(define-step check-rules
  (atomic verify compliance document "项目书.docx" rules (list "rule-1" "rule-2" "rule-3"))
  #:when #t
  #:next generate-output)

(define-step generate-output
  (atomic create-report generate data results template "标准模板")
  #:next notify-result)

(define-step notify-result
  (atomic send-message notify channel "email" message "处理完成"))

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
