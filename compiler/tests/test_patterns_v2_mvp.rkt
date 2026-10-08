#lang racket/base

(require rackunit
         rackunit/text-ui
         racket/function
         racket/file
         racket/port
         racket/path
         racket/string
         "../patterns_v2.rkt")

(define FIXTURES-V2-DIR-PARTS
  (list (current-directory) ".." ".." "tests" "patterns" "fixtures_v2"))

(define (fixture-v2-path basename)
  (apply build-path (append FIXTURES-V2-DIR-PARTS (list basename))))

(define N 200)

(define (fixture->expanded-sexps al-path)
  (call-with-input-file al-path
    (lambda (in)
      (define current-mod-ns (variable-reference->namespace (#%variable-reference)))
      (let loop ((acc '()))
        (define v (read in))
        (if (eof-object? v)
            (reverse acc)
            (loop (cons (eval v current-mod-ns) acc)))))))

(define (normalize-sexp str)
  (with-input-from-string str
    (thunk
      (let loop ((tok (read)) (out '()))
        (if (eof-object? tok)
            (string-trim (string-join (reverse out) " "))
            (loop (read) (cons (format "~s" tok) out)))))))

(define (sexps->prefix-text xs n)
  (let ((s (call-with-output-string
            (lambda (out)
              (for ((x (in-list xs)))
                (write x out))))))
    (substring s 0 (min n (string-length s)))))

(define (expected->prefix-text expected-path n)
  (define s (normalize-sexp (file->string expected-path)))
  (substring s 0 (min n (string-length s))))

(define (check-prefix= case-id)
  (let* ((al-path (fixture-v2-path (format "~a.al" case-id)))
         (expected-path (fixture-v2-path (format "~a.expected.rkt" case-id)))
         (expanded (fixture->expanded-sexps al-path))
         (got (sexps->prefix-text expanded N))
         (want (expected->prefix-text expected-path N)))
    (displayln (format "===== V2 ~a first ~a chars =====" case-id N))
    (displayln (format "GOT : ~s" got))
    (displayln (format "WANT: ~s" want))
    (displayln (format "MATCH? = ~a" (equal? got want)))
    (check-equal? got want (format "V2 case ~a first ~a chars mismatch" case-id N))
    #t))

;; CR-41-PAT01..10 10宏 HC 场景（红阶段：define-syntax TODO raise-syntax-error → 全部 10 failures
;; TDD 绿阶段（T8..T17 实现后 → 10 success
(define V2-HC-CASES
  (list "priority01_hc_HC"
        "decomp02_hc_HC"
        "fsm03_hc_HC"
        "eval04_hc_HC"
        "topic05_hc_HC"
        "decom06_hc_HC"
        "guard07_hc_HC"
        "hitl08_hc_HC"
        "exc09_hc_HC"
        "explore10_hc_HC"))

(define-test-suite patterns-v2-mvp-suite
  (for ((cid (in-list V2-HC-CASES)))
    (test-case (format "PATTERNS-V2 ~a HC→define-agent prefix 200 bytes SBE" cid)
      (check-true (check-prefix= cid)))))

(void (run-tests patterns-v2-mvp-suite))
