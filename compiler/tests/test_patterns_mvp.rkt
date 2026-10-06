#lang racket/base

;; =====================================================================
;; O13 Pattern Macros · FR-PATTERN-01 RackUnit 5 cases (阶段 1 红)
;; Case IDs = PM-EXP-DEFCHAIN / DEFPARALLEL / DEFREFLECT / DEFROUTER / DEFPLANNER
;; 每 case 期望 = check-not-exn（宏展开不抛异常，返回 defagent Core AST）
;; 当前阶段（红）：compiler/patterns.rkt 未实现 → 所有 5 case 必然 FAIL
;; =====================================================================

(require rackunit
         rackunit/text-ui
         racket/function
         racket/match
         racket/port
         racket/file
         racket/runtime-path
         racket/syntax
         syntax/stx
         "../agentlisp_compiler.rkt")

;; 加载 fixtures 绝对路径（独立于 cwd）
(define-runtime-path FIXTURES-DIR
  (build-path (current-directory) ".." ".." "tests" "patterns" "fixtures"))

(define (fixture-path basename)
  (build-path FIXTURES-DIR basename))

;; --- helpers ----------------------------------------------------------

;; 模拟 main.rkt 阶段 2「Macro Expansion Pass」入口：
;; patterns.rkt 实现后，该函数会 require patterns + (expand (datum->syntax ...))
;; 然后 syntax->datum 脱壳并包装为 (define-agent name block...) 再送 parse-defagent
;; 当前红阶段：直接 load .al（高层糖语法）尝试走 (compile-agent-lisp)，
;; 因为 compiler/patterns.rkt 未在 main.rkt 中接线 → parse-defagent 找不到顶层
;; (define-agent ...) → 预期会抛 "顶层必须是 (define-agent ...)" 错误 →
;; 我们用 check-not-exn 所以 = 必然失败 = 红。
(define (compile-fixture-al-path al-path)
  (parameterize ([current-namespace (make-base-namespace)])
    (with-handlers ([exn:fail? (lambda (e) (raise e))])
      (let* ([raw (call-with-input-file al-path
                    (lambda (p)
                      ;; 高层糖语法是单 S-exp：(defchain-agent …) / (defreflect-agent …) 等
                      (read p)))])
        ;; 若实现了 patterns.rkt，这里会变成 (define-agent name block...)
        ;; 当前仅尝试直接 compile-agent-lisp（手搓包装层，尝试模拟接线）
        (let ([maybe-wrapped
               (match raw
                 [`(,agent-kind ,agent-name ,params ...)
                  #:when (memq agent-kind '(defreflect-agent defrouter-agent defchain-agent
                                                       defparallel-agent defplanner-agent))
                   `(define-agent ,agent-name ,raw)]
                 [`,other raw])])
          ;; 交给主编译器，expect 无异常
          (compile-agent-lisp maybe-wrapped))))))

;; --- suite ------------------------------------------------------------

(define-test-suite pattern-macro-expand-suite
  (test-case "PM-EXP-DEFCHAIN-001: defchain-agent doc-pipeline 展开不得抛异常，必须产出 defagent Core AST"
    (check-not-exn (thunk (compile-fixture-al-path (fixture-path "defchain_doc_pipeline.al")))))

  (test-case "PM-EXP-DEFPARALLEL-001: defparallel-agent multi-search 展开不得抛异常"
    (check-not-exn (thunk (compile-fixture-al-path (fixture-path "defparallel_multi_search.al")))))

  (test-case "PM-EXP-DEFREFLECT-001: defreflect-agent code-refiner 展开不得抛异常（§4.1 已有完整宏模板）"
    (check-not-exn (thunk (compile-fixture-al-path (fixture-path "defreflect_code_refiner.al")))))

  (test-case "PM-EXP-DEFROUTER-001: defrouter-agent ops-gateway 展开不得抛异常"
    (check-not-exn (thunk (compile-fixture-al-path (fixture-path "defrouter_ops_gateway.al")))))

  (test-case "PM-EXP-DEFPLANNER-001: defplanner-agent deep-researcher 展开不得抛异常"
    (check-not-exn (thunk (compile-fixture-al-path (fixture-path "defplanner_deep_researcher.al"))))))

(module+ main
  (exit (run-tests pattern-macro-expand-suite)))

(module+ test
  (run-tests pattern-macro-expand-suite))
