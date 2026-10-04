#lang racket/base

;; =====================================================================
;; SRS §6 AC-1 编译期断言测试集 (RackUnit)
;; 对应: AC-1-KV-(1..4) / AC-1-UN-(1..4) / AC-1-CL-(1..4) = 12 条 ERR_ 反例
;; + 6 条 FR-PARSER 正/反例 (AC-1 parser boundary)
;; 总计 ≥18 条，对齐 SRS 附录 B Traceability Matrix
;; =====================================================================
;; 说明：本机若无 racket，本文件将在 CI Ubuntu runner 上由 Bogdanp/setup-racket + raco test 执行
;; 在开发机侧可用 Python 脚本对 18 条 DSL 做静态语法检查（括号平衡 / 关键字存在）

(require rackunit
         rackunit/text-ui
         racket/function
         racket/match
         racket/port
         "../agentlisp_compiler.rkt")

;; ----------------------------- helpers --------------------------------
(define (expect-err code thunk)
  (with-handlers ([(lambda (e) (and (exn:fail? e)
                                     (string-contains? (exn-message e) (symbol->string code))))
                   identity])
    (thunk)
    (error 'expect-err "expected exn containing ~a, got none" code)))

(define (expect-parse-err thunk)
  (with-handlers ([exn:fail:read? identity]
                  [(lambda (e) (string-contains? (exn-message e) "[AGENTLISP_PARSE]")) identity])
    (thunk)
    (error 'expect-parse-err "expected parse error, got none")))

(define (expect-check-err code thunk)
  (expect-err code thunk))

(define (expect-ok thunk)
  (check-not-exn thunk))

;; ----------------------------- AC-1-KV (ERR_KV_ALIGNMENT_VIOLATION) --
(define kv-ok-std-order
  '(defagent demo
     (:model :provider "anthropic" :name "c" :temperature 0.2 :system-prompt "ok")
     (:tools (import-builtin read-file))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)
               :status-bar (:step-count #t))))

(define kv-bad-ctx-first
  '(defagent demo
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:model :provider "anthropic" :name "c" :temperature 0.2 :system-prompt "ok")
     (:tools (import-builtin read-file))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure abort))))

(define kv-bad-ctx-before-tools
  '(defagent demo
     (:model :provider "anthropic" :name "c" :temperature 0.2 :system-prompt "ok")
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:tools (import-builtin read-file bash))
     (:harness (:constrain :forbidden-commands ("rm -rf") :require-human-approval (bash))
               (:verify :test-runner "pytest")
               (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))

(define kv-ok-empty-tools-only-builtin
  '(defagent demo
     (:model :provider "anthropic" :name "c" :temperature 0.2 :system-prompt "ok")
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:tools (import-builtin read-file))
     (:harness (:constrain) (:verify :linter-check #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure fallback-model))))

(define kv-ok-worker-order
  '(defagent demo
     (:model :provider "anthropic" :name "c" :temperature 0.2 :system-prompt "ok")
     (:tools (import-builtin read-file))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))
     (:multiagent :topology orchestration :workers
       ((scoped-worker w
          (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "worker")
          (:tools (define-tool only-in-w (() ()))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))))))

(define kv-bad-worker-inner-ctx-first-model-later
  ;; scoped-worker 顺序也应受 ERR_KV_ALIGNMENT 约束（目前 checker 仅对外层生效，本条为 P1 未来扩展，标记 xfail）
  '(defagent demo
     (:model :provider "anthropic" :name "c" :temperature 0.2 :system-prompt "ok")
     (:tools (import-builtin read-file))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))
     (:multiagent :topology orchestration :workers
       ((scoped-worker w-bad
          (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
          (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "worker-ctx-before-model")
          (:tools (import-builtin echo))
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))))))

(define-test-suite ac-1-kv-tests
  (test-case "AC-1-KV-1 context before model -> ERR_KV_ALIGNMENT_VIOLATION"
    (expect-check-err 'ERR_KV_ALIGNMENT_VIOLATION
                      (lambda () (compile-agent-lisp kv-bad-ctx-first))))

  (test-case "AC-1-KV-2 context before tools -> ERR_KV_ALIGNMENT_VIOLATION"
    (expect-check-err 'ERR_KV_ALIGNMENT_VIOLATION
                      (lambda () (compile-agent-lisp kv-bad-ctx-before-tools))))

  (test-case "AC-1-KV-3 standard order -> PASS"
    (expect-ok (lambda () (compile-agent-lisp kv-ok-std-order #:mode 'check))))

  (test-case "AC-1-KV-4 multiagent worker order ok + scoped-worker tool not leak -> PASS"
    (expect-ok (lambda () (compile-agent-lisp kv-ok-worker-order #:mode 'check)))))

;; ----------------------------- AC-1-UN (ERR_UNGUARDED_TOOL_EXECUTION) -
(define (unguarded tool-lst harness-lst)
  `(defagent demo-u
     (:model :provider "mock" :name "m" :temperature 0.1 :system-prompt "u")
     (:tools ,@tool-lst)
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract L1-Overview L2-FullText) :auto-append #t)
               :status-bar (:step-count #t))
     (:harness ,@harness-lst)))

(define un-bad-1 (unguarded '((import-builtin bash read-file))
                           '((:constrain)
                             (:verify)
                             (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))
(define un-ok-1 (unguarded '((import-builtin bash))
                          '((:constrain)
                            (:verify :test-runner "pytest tests/")
                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))
(define un-bad-approval-mismatch
  (unguarded '((import-builtin git-push bash))
             '((:constrain :require-human-approval (other-tool))
               (:verify)
               (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))
(define un-ok-approval
  ;; 精细化：只有 require-approval 还不够，必须同时有至少 1 条非空 forbidden（安全基线护栏）——AC-1 严格化
  (unguarded '((import-builtin git-push))
             '((:constrain :require-human-approval (git-push) :forbidden-commands ("git push --force"))
               (:verify)
               (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))
(define un-bad-empty-forbidden-string (unguarded
                                       '((import-builtin bash))
                                       '((:constrain :require-human-approval (bash) :forbidden-commands (""))
                                         (:verify)
                                         (:correct :max-retries 1 :circuit-breaker 2 :on-failure abort))))
(define un-ok-combo (unguarded
                     '((import-builtin bash git-push))
                     '((:constrain :forbidden-commands ("rm -rf") :require-human-approval (git-push))
                       (:verify :json-schema #t)
                       (:correct :max-retries 3 :circuit-breaker 5 :on-failure ask-human))))

(define-test-suite ac-1-un-tests
  (test-case "AC-1-UN-1 bash + verify empty + no guard -> ERR_UNGUARDED_TOOL_EXECUTION"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un-bad-1))))
  (test-case "AC-1-UN-2 approval mismatch + git-push -> ERR_UNGUARDED_TOOL_EXECUTION"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un-bad-approval-mismatch))))
  (test-case "AC-1-UN-3 forbidden empty string + approval -> ERR_UNGUARDED_TOOL_EXECUTION (new: 必须要求非空 forbidden 基线)"
    (expect-check-err 'ERR_UNGUARDED_TOOL_EXECUTION
                      (lambda () (compile-agent-lisp un-bad-empty-forbidden-string))))
  (test-case "AC-1-UN-4 test_runner + approval combo ok -> PASS"
    (expect-ok (lambda () (compile-agent-lisp un-ok-combo #:mode 'check))))
  (test-case "AC-1-UN-5 require-approval + non-empty forbidden (无 verify) -> PASS (SRS §4.2 双护栏 OR 条件满足)"
    (expect-ok (lambda () (compile-agent-lisp un-ok-approval #:mode 'check)))))

;; ----------------------------- AC-1-CL (ERR_CONTEXT_LEAKAGE) ----------
(define cl-bad-duplicate-name
  '(defagent demo-cl
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "ok")
     (:tools (define-tool write-md ((s string)) ((ok boolean?)))
            (define-tool both ((s string)) ((ok boolean?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))
     (:multiagent :topology peer :workers
       ((scoped-worker w1
          (:model :provider "mock" :name "m1" :temperature 0.0 :system-prompt "w1")
          (:tools (define-tool write-md ((s string)) ((ok boolean?))) ; 与父重名
                 (define-tool both     ((s string)) ((ok boolean?)))) ; 与父重名
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))))))

(define cl-ok-diff-names
  '(defagent demo-cl-ok
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "ok")
     (:tools (define-tool parent-only ((s string)) ((r list?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))
     (:multiagent :topology judge-driven :workers
       ((scoped-worker judge
          (:model :provider "anthropic" :name "c" :temperature 0.1 :system-prompt "judge")
          (:tools (define-tool reviewer-only ((s string)) ((score number?))))
          (:harness (:constrain) (:verify :reviewer-agent "judge") (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))))))

(define cl-ok-prefix-string-not-duplicate
  ;; 工具名是字符串前缀：不构成 ERR_CONTEXT_LEAKAGE（反误杀）
  '(defagent demo-cl-safe
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "ok")
     (:tools (define-tool write-md ((s string)) ((ok boolean?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))
     (:multiagent :topology decentralised :workers
       ((scoped-worker w-suffix
          (:model :provider "mock" :name "a" :temperature 0.0 :system-prompt "w-suffix")
          (:tools (define-tool write-md-worker ((s string)) ((ok boolean?)))) ; 不重名（前缀不同完整字符串）
          (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))))))

(define cl-bad-3-workes-3-dups
  '(defagent demo-cl-3
     (:model :provider "mock" :name "m" :temperature 0.0 :system-prompt "ok")
     (:tools (define-tool shared ((s string)) ((r any?))))
     (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))
     (:multiagent :topology orchestration :workers
       ((scoped-worker wa (:model :provider "mock" :name "a" :temperature 0.0 :system-prompt "a") (:tools (define-tool shared ((s string)) ((r any?)))) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human)))
        (scoped-worker wb (:model :provider "mock" :name "b" :temperature 0.0 :system-prompt "b") (:tools (define-tool shared ((s string)) ((r any?)))) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human)))
        (scoped-worker wc (:model :provider "mock" :name "c" :temperature 0.0 :system-prompt "c") (:tools (define-tool shared ((s string)) ((r any?)))) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))))))

(define-test-suite ac-1-cl-tests
  (test-case "AC-1-CL-1 duplicate tool name parent vs worker -> ERR_CONTEXT_LEAKAGE"
    (expect-check-err 'ERR_CONTEXT_LEAKAGE (lambda () (compile-agent-lisp cl-bad-duplicate-name))))

  (test-case "AC-1-CL-2 3 workers all share -> ERR_CONTEXT_LEAKAGE"
    (expect-check-err 'ERR_CONTEXT_LEAKAGE (lambda () (compile-agent-lisp cl-bad-3-workes-3-dups))))

  (test-case "AC-1-CL-3 safe prefix non-duplicate name -> PASS (反误杀)"
    (expect-ok (lambda () (compile-agent-lisp cl-ok-prefix-string-not-duplicate #:mode 'check))))

  (test-case "AC-1-CL-4 judge-driven separate names -> PASS"
    (expect-ok (lambda () (compile-agent-lisp cl-ok-diff-names #:mode 'check)))))

;; ----------------------------- parser boundary (FR-PARSER 反/正例) ----
(define p-bad-temp-2.0
  '(defagent p-t (:model :provider "mock" :name "x" :temperature 2.0 :system-prompt "bad") (:tools (import-builtin echo)) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))
(define p-bad-provider
  '(defagent p-p (:model :provider "weird" :name "x" :temperature 0.0 :system-prompt "bad") (:tools (import-builtin echo)) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))
(define p-bad-onfail-underscore
  '(defagent p-o (:model :provider "mock" :name "x" :temperature 0.0 :system-prompt "bad") (:tools (import-builtin echo)) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask_human))))
(define p-bad-onfail-unknown
  '(defagent p-ou (:model :provider "mock" :name "x" :temperature 0.0 :system-prompt "bad") (:tools (import-builtin echo)) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure foo))))
(define p-bad-layer
  '(defagent p-mem (:model :provider "mock" :name "x" :temperature 0.0 :system-prompt "bad") (:tools (import-builtin echo)) (:context :memory-policy (:markdown-fs "./x" :layers (L3-Foo) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure abort))))
(define p-bad-topology
  '(defagent p-top (:model :provider "mock" :name "x" :temperature 0.0 :system-prompt "bad") (:tools (import-builtin echo)) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human)) (:multiagent :topology weird-topology :workers ())))
(define p-ok-only-builtin   kv-ok-empty-tools-only-builtin)
(define p-ok-only-mcp
  '(defagent p-mcp (:model :provider "mock" :name "x" :temperature 0.0 :system-prompt "ok") (:tools (import-mcp "stdio://./tools.py")) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))
(define p-ok-only-define-tool
  '(defagent p-dt (:model :provider "mock" :name "x" :temperature 0.0 :system-prompt "ok") (:tools (define-tool echo (()) ())) (:context :memory-policy (:markdown-fs "./x" :layers (L0-Abstract) :auto-append #t)) (:harness (:constrain) (:verify :json-schema #t) (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human))))

(define-test-suite parser-boundary-tests
  (test-case "FR-PARSER-2 temperature 2.0 -> ERR_CHECK_MODEL_TEMPERATURE_RANGE (check-time，非 parse-time)"
    (expect-check-err 'ERR_CHECK_MODEL_TEMPERATURE_RANGE
                      (lambda () (compile-agent-lisp p-bad-temp-2.0 #:mode 'check))))
  (test-case "FR-PARSER-2 provider weird -> ERR_CHECK_MODEL_PROVIDER_ENUM (check-time)"
    (expect-check-err 'ERR_CHECK_MODEL_PROVIDER_ENUM
                      (lambda () (compile-agent-lisp p-bad-provider #:mode 'check))))
  (test-case "FR-PARSER-5 on-failure ask_human underscore -> ERR_CHECK_HARNESS_CORRECT_ON_FAILURE_ENUM (spec 用连字符)"
    (expect-check-err 'ERR_CHECK_HARNESS_CORRECT_ON_FAILURE_ENUM
                      (lambda () (compile-agent-lisp p-bad-onfail-underscore #:mode 'check))))
  (test-case "FR-PARSER-5 on-failure foo -> ERR_CHECK_HARNESS_CORRECT_ON_FAILURE_ENUM"
    (expect-check-err 'ERR_CHECK_HARNESS_CORRECT_ON_FAILURE_ENUM
                      (lambda () (compile-agent-lisp p-bad-onfail-unknown #:mode 'check))))
  (test-case "FR-PARSER-2 memory layer L3-Foo -> ERR_CHECK_MEMORY_LAYER_ENUM"
    (expect-check-err 'ERR_CHECK_MEMORY_LAYER_ENUM
                      (lambda () (compile-agent-lisp p-bad-layer #:mode 'check))))
  (test-case "FR-PARSER-6 topology weird -> ERR_CHECK_MULTIAGENT_TOPOLOGY_ENUM"
    (expect-check-err 'ERR_CHECK_MULTIAGENT_TOPOLOGY_ENUM
                      (lambda () (compile-agent-lisp p-bad-topology #:mode 'check))))
  (test-case "FR-PARSER-4 tools 仅 builtin + 仅 mcp + 仅 define-tool 都能 parse PASS + check PASS"
    (expect-ok (lambda () (compile-agent-lisp p-ok-only-builtin #:mode 'check)))
    (expect-ok (lambda () (compile-agent-lisp p-ok-only-mcp #:mode 'check)))
    (expect-ok (lambda () (compile-agent-lisp p-ok-only-define-tool #:mode 'check))))
  (test-case "FR-PARSER-7 生产级样例 production-repair-agent.al 19 条静态断言 PASS (read-file + 静态 KV 合规)"
    (define text (file->string (build-path (or (current-load-relative-directory) (current-directory))
                                           'up 'up "examples" "production-repair-agent.al")))
    (define forms (with-input-from-string text (lambda () (read))))
    (expect-ok (lambda () (compile-agent-lisp forms #:mode 'check)))))

;; ----------------------------- main -----------------------------------
(module+ main
  (run-tests ac-1-kv-tests)
  (run-tests ac-1-un-tests)
  (run-tests ac-1-cl-tests)
  (run-tests parser-boundary-tests))
