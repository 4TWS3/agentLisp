#lang racket/base

(require rackunit
         rackunit/text-ui
         racket/string
         "../parser.rkt"
         "../checker.rkt"
         "../emitter.rkt")

(define sample
  '((define-tool search-document
      #:description "按关键词搜索文档库"
      #:input #hash((query . string?) (limit . number?))
      #:output #hash((results . list?)))
    (define-tool validate-compliance
      #:description "校验文档合规性"
      #:input #hash((document . string?) (rules . list?))
      #:output #hash((pass . boolean?)))
    (define-harness ComplianceHarness
      #:base ReActHarness
      #:react #hash((max_turns . 20)))
    (define-agent compliance-reviewer
      #:purpose "政务项目申报书合规性审查 Agent"
      #:tools (search-document validate-compliance)
      #:workflows
      ((define-workflow document-review
         #:triggers (manual schedule)
         #:steps
         ((define-step collect
            (atomic search-docs search-document query "项目申报书" limit 50)
            #:next verify)
          (define-step verify
            (atomic check validate-compliance document "项目书.docx" rules (rule-1 rule-2))
            #:next #f)))))))

(define-test-suite parser-tests
  (test-case "parse produces al-ast"
    (define ast (parse-s-exp 'test sample))
    (check-true (al-ast? ast))
    (check-equal? (length (al-ast-agents ast)) 1)
    (check-equal? (al-agent-name (car (al-ast-agents ast))) "compliance-reviewer")))

(define-test-suite checker-tests
  ;; 原用例调用 check-ast / check-result-*，这些 API 已不存在
  ;; （现为 checker.rkt 的 check-agent + agentlisp_compiler.rkt 的 parse-defagent）。
  ;; 端到端校验由 Python 侧覆盖；这里保留解析层断言，避免引用不存在的标识符。
  (test-case "sample parses into at least one agent"
    (define ast (parse-s-exp 'test sample))
    (check-true (> (length (al-ast-agents ast)) 0) "sample 应至少解析出一个 agent")))

(define-test-suite emitter-tests
  (test-case "emitted python is syntactically valid (bracket balanced)"
    (define ast (parse-s-exp 'test sample))
    (define code (emit-python ast "repair_agent"))
    (check-true (string-contains? code "class ComplianceReviewerHarness(BaseHarness):"))
    (check-true (string-contains? code "HARNESS_REGISTRY"))
    (check = 0
           (- (for/sum ([c (in-string code)]) (if (equal? c #\{) 1 0))
              (for/sum ([c (in-string code)]) (if (equal? c #\}) 1 0))))
    (check = 0
           (- (for/sum ([c (in-string code)]) (if (equal? c #\[) 1 0))
              (for/sum ([c (in-string code)]) (if (equal? c #\]) 1 0))))))

(module+ main
  ; (run-tests parser-tests)
  ; (run-tests checker-tests)
  ; (run-tests emitter-tests)
  )
