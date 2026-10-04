#lang racket/base

(require rackunit
         rackunit/text-ui
         "../agent-dsl/main.rkt")

(define-test-suite agent-struct-tests
  (test-case "agent struct creation"
    (let ([ag (agent "test" "purpose" '() '())])
      (check-true (agent? ag))
      (check-equal? (agent-name ag) "test")
      (check-equal? (agent-purpose ag) "purpose"))))

(define-test-suite macro-definition-tests
  (test-case "define-tool creates valid tool"
    (define-tool t1 #:description "d" #:input '#hash() #:output '#hash())
    (check-true (tool? t1))
    (check-equal? (tool-name t1) "t1")
    (check-equal? (tool-description t1) "d"))

  (test-case "define-agent creates valid agent"
    (define-tool dummy-t)
    (define-workflow dummy-w #:steps ())
    (define-agent my-agent
      #:purpose "test purpose"
      #:tools (dummy-t)
      #:workflows (dummy-w))
    (check-true (agent? my-agent))
    (check-equal? (agent-name my-agent) "my-agent")
    (check-equal? (agent-purpose my-agent) "test purpose")
    (check-equal? (length (agent-tools my-agent)) 1)
    (check-equal? (length (agent-workflows my-agent)) 1)))

(define-test-suite validation-tests
  (test-case "validate-agent accepts valid agent"
    (define-agent valid-ag
      #:purpose "p"
      #:tools ()
      #:workflows ())
    (let-values ([(ok? msg) (validate-agent valid-ag)])
      (check-true ok?)
      (check-equal? msg "Valid")))

  (test-case "validate-agent rejects non-agent"
    (let-values ([(ok? msg) (validate-agent "not an agent")])
      (check-false ok?))))

(define-test-suite serialization-tests
  (test-case "serialize-agent produces hash"
    (define-agent ser-ag
      #:purpose "serialize test"
      #:tools ()
      #:workflows ())
    (let ([h (serialize-agent ser-ag)])
      (check-true (hash? h))
      (check-equal? (hash-ref h 'name) "ser-ag")
      (check-equal? (hash-ref h 'type) "agent"))))

(module+ main
  (run-tests agent-struct-tests)
  (run-tests macro-definition-tests)
  (run-tests validation-tests)
  (run-tests serialization-tests))
