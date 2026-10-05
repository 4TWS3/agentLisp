#lang racket/base

;; =====================================================================
;; CR-34 O4 AC-1: RackUnit 18 cases 精确位对齐 SRS §6.1 判定表
;; 3 ERR × (4 反例 expect-check-err + 2 正例 expect-ok) = 18 cases
;; Case IDs 与 Python pytest 镜像全等（字节对齐）：
;;   KV-1neg..KV-4neg / KV-5pos..KV-6pos
;;   UN-1neg..UN-4neg / UN-5pos..UN-6pos
;;   CL-1neg..CL-4neg / CL-5pos..CL-6pos
;; =====================================================================

(require rackunit
         rackunit/text-ui
         "../agentlisp_compiler.rkt")

(define (expect-check-err code thunk)
  (with-handlers
    ([(lambda (e)
        (and (exn:fail? e)
             (string-contains? (exn-message e) (symbol->string code))))
      identity])
    (thunk)
    (error 'expect-check-err "expected exn containing ~a, got none" code)))

(define (expect-ok thunk)
  (check-not-exn thunk))

;; ----------------------------- KV (ERR_KV_ALIGNMENT_VIOLATION) 6 cases

(define kv1-ctx-before-model
  '(defagent kv1
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (import-builtin read-file))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define kv2-ctx-before-tools
  '(defagent kv2
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:tools (import-builtin read-file))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define kv3-tools-after-ctx
  '(defagent kv3
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:tools (import-builtin bash))
     (:harness (:constrain :forbidden-commands ("rm") :require-human-approval (bash))
               (:verify)
               (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define kv4-model-after-ctx
  '(defagent kv4
     (:tools (import-builtin read-file))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define kv5-std-order-pos
  '(defagent kv5
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (import-builtin read-file))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define kv6-std-with-harness-pos
  '(defagent kv6
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (import-builtin read-file))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))))

;; ----------------------------- UN (ERR_UNGUARDED_TOOL_EXECUTION) 6 cases

(define (unguarded-agent builtins harness)
  `(defagent u
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (import-builtin ,@builtins))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness ,@harness)))

(define un1-gitpush-noguard
  (unguarded-agent '(git-push read-file)
                   '((:constrain) (:verify) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define un2-bash-approval-no-forbidden
  (unguarded-agent '(bash)
                   '((:constrain :require-human-approval (bash) :forbidden-commands ())
                     (:verify)
                     (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define un3-curl-forbidden-empty-str
  (unguarded-agent '(curl)
                   '((:constrain :require-human-approval (curl) :forbidden-commands ("" "  "))
                     (:verify)
                     (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define un4-sudo-approval-mismatch
  (unguarded-agent '(sudo)
                   '((:constrain :require-human-approval (bash) :forbidden-commands ("rm -rf /"))
                     (:verify)
                     (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define un5-gitpush-approval-and-forbidden-pos
  (unguarded-agent '(git-push)
                   '((:constrain :require-human-approval (git-push) :forbidden-commands ("git push --force"))
                     (:verify)
                     (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

(define un6-bash-verify-testrunner-pos
  (unguarded-agent '(bash)
                   '((:constrain)
                     (:verify :test-runner "pytest")
                     (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))

;; ----------------------------- CL (ERR_CONTEXT_LEAKAGE) 6 cases

(define cl1-father-son-same-write-md
  '(defagent cl1
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (define-tool write-md ((s string)) ((ok boolean?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:multiagent :topology orchestration :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "m1" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool write-md ((s string)) ((ok boolean?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))))))

(define cl2-old-key-define-tools-dup
  '(defagent cl2
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (define-tool read-xls ((f string)) ((rows list?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:multiagent :topology orchestration :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "m1" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool read-xls ((f string)) ((rows list?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))))))

(define cl3-brothers-same-check-rule
  '(defagent cl3
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools)
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:multiagent :topology peer :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "a" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool check-rule ((r list?)) ((ok boolean?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort)))
        (scoped-worker w2
          (:model :provider "mock" :name "b" :temperature 0.0 :system-prompt "w2")
          (:tools (define-tool check-rule ((r list?)) ((ok boolean?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))))))

(define cl4-brothers-string-dup-run-shell
  '(defagent cl4
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools)
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:multiagent :topology peer :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "a" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool run-shell (()) ()))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort)))
        (scoped-worker w2
          (:model :provider "mock" :name "b" :temperature 0.0 :system-prompt "w2")
          (:tools (define-tool run-shell (()) ()))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))))))

(define cl5-prefix-safe-not-dup-pos
  '(defagent cl5
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (define-tool write-md ((s string)) ((ok boolean?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:multiagent :topology orchestration :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "m1" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool write-md-worker ((s string)) ((ok boolean?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))))))

(define cl6-three-brothers-diff-names-pos
  '(defagent cl6
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "p")
     (:tools (define-tool father ((s string)) ((ok boolean?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))
     (:multiagent :topology orchestration :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "a" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool a ((x string)) ((r list?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort)))
        (scoped-worker w2
          (:model :provider "mock" :name "b" :temperature 0.0 :system-prompt "w2")
          (:tools (define-tool b ((x string)) ((r list?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort)))
        (scoped-worker w3
          (:model :provider "mock" :name "c" :temperature 0.0 :system-prompt "w3")
          (:tools (define-tool c ((x string)) ((r list?))))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))))))

;; ----------------------------- suites ---------------------------------

(define-test-suite ac1-kv-suite
  (test-case "KV-1neg: context before model -> ERR_KV_ALIGNMENT_VIOLATION"
    (expect-check-err 'ERR_KV_ALIGNMENT_VIOLATION
                      (lambda () (compile-agent-lisp kv1-ctx-before-model))))
  (test-case "KV-2neg: context before tools -> ERR_KV_ALIGNMENT_VIOLATION"
    (expect-check-err 'ERR_KV_ALIGNMENT_VIOLATION
                      (lambda () (compile-agent-lisp kv2-ctx-before-tools))))
  (test-case "KV-3neg: tools after context -> ERR_KV_ALIGNMENT_VIOLATION"
    (expect-check-err 'ERR_KV_ALIGNMENT_VIOLATION
                      (lambda () (compile-agent-lisp kv3-tools-after-ctx))))
  (test-case "KV-4neg: model after context -> ERR_KV_ALIGNMENT_VIOLATION"
    (expect-check-err 'ERR_KV_ALIGNMENT_VIOLATION
                      (lambda () (compile-agent-lisp kv4-model-after-ctx))))
  (test-case "KV-5pos: standard order model/tools/context -> PASS"
    (expect-ok (lambda () (compile-agent-lisp kv5-std-order-pos #:mode 'check))))
  (test-case "KV-6pos: harness between tools and context -> PASS"
    (expect-ok (lambda () (compile-agent-lisp kv6-std-with-harness-pos #:mode 'check)))))

(define-test-suite ac1-un-suite
  (test-case "UN-1neg: git-push no guard at all -> ERR_UNGUARDED_TOOL_EXECUTION"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un1-gitpush-noguard))))
  (test-case "UN-2neg: bash approval present but forbidden empty list -> ERR_UNGUARDED_TOOL_EXECUTION"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un2-bash-approval-no-forbidden))))
  (test-case "UN-3neg: curl forbidden only empty strings -> ERR_UNGUARDED_TOOL_EXECUTION"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un3-curl-forbidden-empty-str))))
  (test-case "UN-4neg: sudo approval list mismatch (only bash) -> ERR_UNGUARDED_TOOL_EXECUTION"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un4-sudo-approval-mismatch))))
  (test-case "UN-5pos: git-push approval + non-empty forbidden (Guard A) -> PASS"
    (expect-ok (lambda () (compile-agent-lisp un5-gitpush-approval-and-forbidden-pos #:mode 'check))))
  (test-case "UN-6pos: bash verify.test_runner (Guard B) -> PASS"
    (expect-ok (lambda () (compile-agent-lisp un6-bash-verify-testrunner-pos #:mode 'check)))))

(define-test-suite ac1-cl-suite
  (test-case "CL-1neg: father/son define-tool write-md exact dup -> ERR_CONTEXT_LEAKAGE"
    (expect-check-err 'ERR_CONTEXT_LEAKAGE
                      (lambda () (compile-agent-lisp cl1-father-son-same-write-md))))
  (test-case "CL-2neg: father/son define-tool read-xls dup (old key path) -> ERR_CONTEXT_LEAKAGE"
    (expect-check-err 'ERR_CONTEXT_LEAKAGE
                      (lambda () (compile-agent-lisp cl2-old-key-define-tools-dup))))
  (test-case "CL-3neg: brothers both define check-rule -> ERR_CONTEXT_LEAKAGE"
    (expect-check-err 'ERR_CONTEXT_LEAKAGE
                      (lambda () (compile-agent-lisp cl3-brothers-same-check-rule))))
  (test-case "CL-4neg: brothers both define string tool run-shell -> ERR_CONTEXT_LEAKAGE"
    (expect-check-err 'ERR_CONTEXT_LEAKAGE
                      (lambda () (compile-agent-lisp cl4-brothers-string-dup-run-shell))))
  (test-case "CL-5pos: father write-md vs son write-md-worker (prefix) -> PASS (反误杀)"
    (expect-ok (lambda () (compile-agent-lisp cl5-prefix-safe-not-dup-pos #:mode 'check))))
  (test-case "CL-6pos: three brothers tools a/b/c distinct + father 'father' -> PASS"
    (expect-ok (lambda () (compile-agent-lisp cl6-three-brothers-diff-names-pos #:mode 'check)))))

(module+ main
  (run-tests ac1-kv-suite)
  (run-tests ac1-un-suite)
  (run-tests ac1-cl-suite))
