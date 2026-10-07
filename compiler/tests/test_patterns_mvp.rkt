#lang racket/base

(require rackunit
         rackunit/text-ui
         racket/function
         racket/file
         racket/port
         racket/path
         racket/runtime-path
         "../patterns.rkt")

(define-runtime-path FIXTURES-DIR
  (build-path (current-directory) ".." ".." "tests" "patterns" "fixtures"))

(define (fixture-path basename)
  (build-path FIXTURES-DIR basename))

(define N 200)

(define *ns* (current-namespace))

(define (fixture->expanded-sexps al-path)
  (call-with-input-file al-path
    (lambda (in)
      (parameterize ((current-namespace *ns*))
        (let loop ((acc '()))
          (define v (read in))
          (if (eof-object? v)
              (reverse acc)
              (loop (cons (eval v) acc))))))))

(define (sexps->prefix-text xs n)
  (let ((s (call-with-output-string
            (lambda (out)
              (for ((x (in-list xs)))
                (write x out)
                (newline out))))))
    (substring s 0 (min n (string-length s)))))

(define (expected->prefix-text expected-path n)
  (define s (file->string expected-path))
  (substring s 0 (min n (string-length s))))

(define (check-prefix= al-name)
  (let* ((al-path (fixture-path (format "~a.al" al-name)))
         (expected-path (fixture-path (format "~a.expected.rkt" al-name)))
         (expanded (fixture->expanded-sexps al-path))
         (got (sexps->prefix-text expanded N))
         (want (expected->prefix-text expected-path N)))
    (displayln (format "===== ~a first ~a chars =====" al-name N))
    (displayln (format "GOT : ~s" got))
    (displayln (format "WANT: ~s" want))
    (displayln (format "MATCH? = ~a" (equal? got want)))
    (check-equal? got want (format "~a first ~a chars mismatch" al-name N))
    #t))

(define-test-suite pattern-macro-expand-suite
  (test-case "PM-EXP-DEFREFLECT-001: defreflect-agent code-refiner expand 200chars == expected"
    (check-prefix= "defreflect_code_refiner"))
  (test-case "PM-EXP-DEFROUTER-001: defrouter-agent ops-gateway expand 200chars == expected"
    (check-prefix= "defrouter_ops_gateway"))
  (test-case "PM-EXP-DEFCHAIN-001: defchain-agent doc-pipeline expand 200chars == expected"
    (check-prefix= "defchain_doc_pipeline"))
  (test-case "PM-EXP-DEFPARALLEL-001: defparallel-agent multi-search expand 200chars == expected"
    (check-prefix= "defparallel_multi_search"))
  (test-case "PM-EXP-DEFPLANNER-001: defplanner-agent deep-researcher expand 200chars == expected"
    (check-prefix= "defplanner_deep_researcher")))

(module+ main
  (exit (run-tests pattern-macro-expand-suite)))

(module+ test
  (run-tests pattern-macro-expand-suite))
