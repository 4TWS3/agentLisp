#lang racket/base

(require (for-syntax racket/base
                     racket/syntax
                     racket/string
                     racket/match)
         (for-meta 2 racket/base
                   racket/syntax))

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

(define-for-syntax (v2-model-kw k)
  (memq k '(:provider :name :model-name :temperature :system-prompt)))
(define-for-syntax (v2-tools-kw k)
  (memq k '(:tools)))
(define-for-syntax (v2-context-kw k)
  (memq k '(:memory-policy :skills :status-bar :context-policy)))
(define-for-syntax (v2-harness-kw k)
  (memq k '(:constrain :verify :correct)))
(define-for-syntax (v2-multiagent-kw k)
  (memq k '(:topology :workers :orchestration)))

(define-for-syntax (v2-plist->blocks pattern-kind plist)
  (define kw->block (make-hash))
  (for-each (lambda (k) (hash-set! kw->block k ':model))
            '(:provider :name :model-name :temperature :system-prompt))
  (for-each (lambda (k) (hash-set! kw->block k ':tools))
            '(:tools))
  (for-each (lambda (k) (hash-set! kw->block k ':context))
            '(:memory-policy :skills :status-bar :context-policy))
  (for-each (lambda (k) (hash-set! kw->block k ':harness))
            '(:constrain :verify :correct))
  (for-each (lambda (k) (hash-set! kw->block k ':multiagent))
            '(:topology :workers :orchestration))
  (define (canon-k k)
    (cond ((keyword? k) (string->keyword (keyword->string k)))
          ((symbol? k) (string->keyword (symbol->string k)))
          (else k)))
  (define buckets (make-hash))
  (define pattern-kvs '())
  (let loop ((xs plist))
    (cond
      ((null? xs) (void))
      ((null? (cdr xs)) (void))
      (else
       (let ((k (car xs)) (v (cadr xs)))
         (define ck (canon-k k))
         (cond
           ((hash-has-key? kw->block ck)
            (define tag (hash-ref kw->block ck))
            (hash-update! buckets tag (lambda (old) (append old (list k v))) (lambda () (list tag))))
           (else
            (set! pattern-kvs (append pattern-kvs (list (list k v))))))
         (loop (cddr xs))))))
  (define blocks
    (for/list ((tag (in-list '(:model :tools :context :harness :multiagent)))
               #:when (hash-has-key? buckets tag))
      (hash-ref buckets tag)))
  (define existing-tags
    (map (lambda (b) (cond ((and (pair? b) (keyword? (car b))) (car b))
                           ((and (pair? b) (symbol? (car b))) (string->keyword (symbol->string (car b))))
                           (else ':notablock)))
         blocks))
  (define required '(:model :tools :context))
  (define to-add (filter (lambda (t) (not (memq t existing-tags))) required))
  (define blocks+defaults
    (append blocks (map (lambda (t) (list t)) to-add)))
  (define pattern-config-block
    (list ':pattern-kind pattern-kind (list ':pattern-config pattern-kvs)))
  (define ma-tag (memq ':multiagent (map (lambda (b) (cond ((and (pair? b) (keyword? (car b))) (car b))
                                                           ((and (pair? b) (symbol? (car b))) (string->keyword (symbol->string (car b))))
                                                           (else ':no))) blocks+defaults)))
  (define blocks+ma
    (if ma-tag
        (map (lambda (b)
               (define tag (cond ((and (pair? b) (keyword? (car b))) (car b))
                                 ((and (pair? b) (symbol? (car b))) (string->keyword (symbol->string (car b))))
                                 (else ':no)))
               (if (eq? tag ':multiagent)
                   (append b (list pattern-config-block))
                   b))
             blocks+defaults)
        (append blocks+defaults (list (list ':multiagent pattern-config-block)))))
  (define tag-order '(:model :tools :context :harness :multiagent))
  (define (tag-of b)
    (cond ((and (pair? b) (keyword? (car b))) (car b))
          ((and (pair? b) (symbol? (car b))) (string->keyword (symbol->string (car b))))
          (else (car tag-order))))
  (sort blocks+ma (lambda (a b)
                    (< (length (memq (tag-of a) tag-order))
                       (length (memq (tag-of b) tag-order))))))

(define-for-syntax (v2-quote-blocks name-sym blocks)
  (with-syntax ((name-sym name-sym)
                ((blk ...) (datum->syntax #'here blocks)))
    #`(list 'define-agent 'name-sym 'blk ...)))


(define-syntax (defpriority-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'priority01-hc #'name*)
     #''(define-agent priority01_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defpriority agent priority01_hc: 使用给定 defpriority 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/priority01_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defpriority)
           (:pattern-config
             (priority-level 3)
             (policies ((safety 0.9) (quality 0.8) (cost 0.6)))
             (routing-table ((urgent => fast-path) (batch => slow-path)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defpriority rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defdecomposition-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'decomp02-hc #'name*)
     #''(define-agent decomp02_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defdecomposition agent decomp02_hc: 使用给定 defdecomposition 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/decomp02_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defdecomposition)
           (:pattern-config
             (subtasks ((ingest "数据接入") (clean "清洗") (analyze "分析")))
             (orchestrator (fan-out 4))
             (rollup (merge-by-timestamp)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defdecomposition rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (deffsm-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'fsm03-hc #'name*)
     #''(define-agent fsm03_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 deffsm agent fsm03_hc: 使用给定 deffsm 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/fsm03_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind deffsm)
           (:pattern-config
             (states (idle running done error))
             (initial idle)
             (final (done error))
             (transitions ((idle start => running) (running ok => done) (running bad => error))))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'deffsm rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defevaluator-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'eval04-hc #'name*)
     #''(define-agent eval04_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defevaluator agent eval04_hc: 使用给定 defevaluator 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/eval04_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defevaluator)
           (:pattern-config
             (rubric ((accuracy 0.5) (speed 0.3) (cost 0.2)))
             (weights (0.5 0.3 0.2))
             (ground-truth "./eval/gt.json")
             (threshold 0.85))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defevaluator rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (deftopic-model-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'topic05-hc #'name*)
     #''(define-agent topic05_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 deftopic-model agent topic05_hc: 使用给定 deftopic-model 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/topic05_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind deftopic-model)
           (:pattern-config
             (topics (tech finance health sports))
             (taxonomy (hierarchical 3 levels))
             (threshold 0.6)
             (clustering (kmeans 8)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'deftopic-model rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defdecomposer-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'decom06-hc #'name*)
     #''(define-agent decom06_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defdecomposer agent decom06_hc: 使用给定 defdecomposer 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/decom06_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defdecomposer)
           (:pattern-config
             (granularity per-paragraph)
             (techniques (mdp-splitting llm-judged heuristic))
             (subagent-pool (worker-a worker-b worker-c))
             (merge weighted-vote))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defdecomposer rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defguardrails-safety-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'guard07-hc #'name*)
     #''(define-agent guard07_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defguardrails-safety agent guard07_hc: 使用给定 defguardrails-safety 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/guard07_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defguardrails-safety)
           (:pattern-config
             (input-policy (pii-filter prompt-injection-detect))
             (output-policy (toxicity-classifier hallucination-rate))
             (audit (full-trace retention 90d))
             (escalation (human-on-threshold 0.85)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defguardrails-safety rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defhitl-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'hitl08-hc #'name*)
     #''(define-agent hitl08_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defhitl agent hitl08_hc: 使用给定 defhitl 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/hitl08_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defhitl)
           (:pattern-config
             (approval-policy (cost>100USD risk>=high pii))
             (escalation (slack "#ops-oncall" SLA 5min))
             (timeout 30min)
             (audit-log (immutable-s3 bucket)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defhitl rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defexception-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'exc09-hc #'name*)
     #''(define-agent exc09_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defexception agent exc09_hc: 使用给定 defexception 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/exc09_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defexception)
           (:pattern-config
             (fallback (degrade-to-cache retry-best-effort))
             (retry-policy (exponential-backoff base 2s max 10))
             (dead-letter (s3 bucket + dlq-notify))
             (monitoring (datadog alarm-threshold 5/5min)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defexception rst-datum)))
       (v2-quote-blocks name-sym blocks))))

(define-syntax (defexploration-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'explore10-hc #'name*)
     #''(define-agent explore10_hc
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.2
                 :system-prompt "CR-41 V2 defexploration agent explore10_hc: 使用给定 defexploration 参数静态配置，运行时遵守 SBE 推导的约束。详见 Pattern Spec §4。")
         (:tools (web-search python-repl read-pdf))
         (:context :memory-policy (markdown-fs "./memory/explore10_hc.md" :layers (L0 L1) :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :cost #t :latency-p95 #t))
         (:harness
           (:constrain (:forbidden-commands ("sudo" "rm -rf /") :human-approval (cost>50)))
           (:verify (:json-schema #t :linter-check ruff :test-runner pytest))
           (:correct (:max-retries 3 :circuit-breaker 10 :on-failure escalate)))
         (:multiagent
           (:pattern-kind defexploration)
           (:pattern-config
             (search-space (hyperparam-range lr (1e-5 1e-2) batch (32 512)))
             (budget (max-trials 200 max-time 2h wall))
             (pruning (median-stop 5%-ile after 5 trials))
             (rollout (ucb-exploration c=2.0)))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (v2-plist->blocks 'defexploration rst-datum)))
       (v2-quote-blocks name-sym blocks)))))
