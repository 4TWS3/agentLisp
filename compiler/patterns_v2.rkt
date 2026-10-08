#lang racket/base

(require (for-syntax racket/base
                     racket/syntax
                     racket/string
                     racket/match))

(provide defpriority-agent
         defdecomposition-agent
         deffsm-agent
         defevaluator-agent
         deftopic-model-agent
         defdecomposer-agent
         defguardrails-safety-agent
         defhitl-agent
         defexception-agent
         defexploration-agent)

(begin-for-syntax
  (define (reorder-blocks/ct blocks)
    (define order-preference
      (hasheq ':model 0
              ':tools 1
              ':context 2
              ':harness 3
              ':multiagent 4))
    (define (tag-of b)
      (define maybe-tag (and (pair? b) (car b)))
      (cond
        ((keyword? maybe-tag) maybe-tag)
        ((symbol? maybe-tag) (string->keyword (symbol->string maybe-tag)))
        (else ':unknown)))
    (define (pref-of tag) (hash-ref order-preference tag 999))
    (sort (for/list ((b (in-list blocks))) b)
          (lambda (a b)
            (< (pref-of (tag-of a)) (pref-of (tag-of b))))))

  (define (plist->blocks/ct plist)
    (define model-kw '(#:provider #:model-name #:temperature #:system-prompt #:max-tokens #:top-p))
    (define model-sym '(provider model-name temperature system-prompt max-tokens top-p model))
    (define model-kw2 (cons '#:model model-kw))
    (define tools-kw '(#:tools #:executor-tools))
    (define tools-sym '(tools executor-tools))
    (define context-kw '(#:context-policy #:context))
    (define context-sym '(context-policy context))
    (define harness-kw '(#:critic #:max-retries #:circuit-breaker #:constrain #:verify #:correct #:reviewer-agent #:forbidden-commands #:require-human-approval #:on-failure #:step-order-assertion #:parallelism-assertion #:plan-completion-assertion #:json-schema #:linter-check #:test-runner #:linter #:reviewer))
    (define harness-sym '(critic max-retries circuit-breaker constrain verify correct reviewer-agent forbidden-commands require-human-approval on-failure step-order-assertion parallelism-assertion plan-completion-assertion json-schema linter-check test-runner linter reviewer harness))
    (define harness-kw2 (cons '#:harness harness-kw))
    (define multiagent-kw '(#:routes #:steps #:branches #:reducer #:planner-prompt #:topology #:workers))
    (define multiagent-sym '(routes steps branches reducer planner-prompt topology workers multiagent))
    (define multiagent-kw2 (cons '#:multiagent multiagent-kw))
    (define kw->block (make-hash))
    (define (collect keyword-list key-sym acc)
      (unless (hash-has-key? kw->block key-sym)
        (hash-set! kw->block key-sym '()))
      (when (pair? acc)
        (hash-set! kw->block key-sym (append (hash-ref kw->block key-sym) (list (cadr acc))))))
    (let loop ((rest plist))
      (cond
        ((null? rest)
         (list (cons ':model (hash-ref kw->block ':model '()))
               (cons ':tools (hash-ref kw->block ':tools '()))
               (cons ':context (hash-ref kw->block ':context '()))
               (cons ':harness (hash-ref kw->block ':harness '()))
               (cons ':multiagent (hash-ref kw->block ':multiagent '()))))
        ((keyword? (car rest))
         (let ((kw (car rest))
               (val (if (pair? (cdr rest)) (cadr rest) #f)))
           (cond
             ((memq kw model-kw2) (collect model-kw2 ':model (list kw val)))
             ((memq kw tools-kw) (collect tools-kw ':tools (list kw val)))
             ((memq kw context-kw) (collect context-kw ':context (list kw val)))
             ((memq kw harness-kw2) (collect harness-kw2 ':harness (list kw val)))
             ((memq kw multiagent-kw2) (collect multiagent-kw2 ':multiagent (list kw val)))
             ((memq kw (list '#:name '#:agent-name '#:priority))
              (hash-set! kw->block ':context (append (hash-ref kw->block ':context '()) (list (list kw val)))))
             (else
              (hash-set! kw->block ':context (append (hash-ref kw->block ':context '()) (list (list kw val))))))
           (if (pair? (cdr rest)) (loop (cddr rest)) (loop '()))))
        (else
         (loop (cdr rest))))))

  (define (ensure-blocks/ct blocks)
    (define tags (map car blocks))
    (define required '(:model :tools :context))
    (append blocks
            (for/list ((t (in-list required)) #:unless (memq t tags))
              (cons t '())))))

(define-syntax (defpriority-agent stx)
  (raise-syntax-error 'defpriority-agent
    (format "CR-41 T8 TODO (HC FIRST GENERIC SECOND first-match plist->blocks 5桶 reorder 升序 0<1<2<3<4 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defdecomposition-agent stx)
  (raise-syntax-error 'defdecomposition-agent
    (format "CR-41 T9 TODO (2层 scoped-worker 子Agent分解 嵌入 harness 5桶升序 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (deffsm-agent stx)
  (raise-syntax-error 'deffsm-agent
    (format "CR-41 T10 TODO (fsm-current-state 原子变量 harness Verify 段注入 状态可达>=2 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defevaluator-agent stx)
  (raise-syntax-error 'defevaluator-agent
    (format "CR-41 T11 TODO (accuracy>=0.8 + safety>=1.0 双 threshold Correct段注入 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (deftopic-model-agent stx)
  (raise-syntax-error 'deftopic-model-agent
    (format "CR-41 T12 TODO (Tools段 scoped-worker(name=topic-processor) context桶topics子树分类器 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defdecomposer-agent stx)
  (raise-syntax-error 'defdecomposer-agent
    (format "CR-41 T13 TODO (Constrain 段 2条 decomposer-schema-field-type-check iso-date/double 断言 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defguardrails-safety-agent stx)
  (raise-syntax-error 'defguardrails-safety-agent
    (format "CR-41 T14 TODO (Harness三段 guardrails 钩子 on-violation Verify->Correct 回路 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defhitl-agent stx)
  (raise-syntax-error 'defhitl-agent
    (format "CR-41 T15 TODO (Constrain human-approval-required-before + Verify waiting-for-human-signal not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defexception-agent stx)
  (raise-syntax-error 'defexception-agent
    (format "CR-41 T16 TODO (Correct段 3层 on-failure retry=3 backoff=1.5x Constrain+Verify+Correct 三层不少 not-implemented yet; stx=~s" (syntax->datum stx))))

(define-syntax (defexploration-agent stx)
  (raise-syntax-error 'defexploration-agent
    (format "CR-41 T17 TODO (Verify 段 budget+convergence 两条 + Correct 段 expand-more-candidates 探索预算+收敛阈值停止 not-implemented yet; stx=~s" (syntax->datum stx))))
