#lang racket/base

(require racket/contract
         racket/match
         racket/list
         racket/string
         syntax/parse/define
         (for-syntax racket/base
                     racket/syntax))

(provide (all-defined-out))

(struct al-agent (name purpose tools harnesses workflows hooks) #:transparent)
(struct al-tool (name description input-schema output-schema) #:transparent)
(struct al-harness (name base-class react-config) #:transparent)
(struct al-workflow (name steps triggers) #:transparent)
(struct al-step (id action next condition) #:transparent)
(struct al-atomic (name target method params) #:transparent)
(struct al-hook (kind target) #:transparent)
(struct al-ast (agents top-level-tools top-level-harnesses) #:transparent)

(define/contract (parse-s-exp source-name exprs)
  (-> any/c list? al-ast?)
  (let loop ([xs exprs]
             [agents '()]
             [tools '()]
             [harnesses '()])
    (cond
      [(null? xs) (al-ast (reverse agents) (reverse tools) (reverse harnesses))]
      [(pair? (car xs))
       (define form (car xs))
       (case (car form)
         [(define-agent)
          (loop (cdr xs) (cons (parse-agent-form (cdr form)) agents) tools harnesses)]
         [(define-tool)
          (loop (cdr xs) agents (cons (parse-tool-form (cdr form)) tools) harnesses)]
         [(define-harness)
          (loop (cdr xs) agents tools (cons (parse-harness-form (cdr form)) harnesses))]
         [(define-workflow)
          (loop (cdr xs) agents tools harnesses)]
         [(define-step atomic)
          (loop (cdr xs) agents tools harnesses)]
         [(include use-harness use-tool require provide begin)
          (loop (cdr xs) agents tools harnesses)]
         [else
          (loop (cdr xs) agents tools harnesses)])]
      [else (loop (cdr xs) agents tools harnesses)])))

(define (parse-agent-form tail)
  (define-values (name rest) (if (null? tail) (values #f '()) (values (car tail) (cdr tail))))
  (let kv-loop ([xs rest] [purpose ""] [tools '()] [workflows '()] [hooks '()] [current-kw #f])
    (cond
      [(null? xs)
       (al-agent (ensure-string/sym name) purpose tools workflows hooks)]
      [(keyword? (car xs))
       (kv-loop (cddr xs) purpose tools workflows hooks (car xs))]
      [else
       (case current-kw
         [(#:purpose) (kv-loop (cdr xs) (car xs) tools workflows hooks #f)]
         [(#:tools)
          (define t-list (flatten (car xs)))
          (kv-loop (cdr xs) purpose (append tools t-list) workflows hooks #f)]
         [(#:workflows)
          (define wf-list
            (for/list ([wf-form (in-list (car xs))])
              (cond
                [(and (pair? wf-form) (eq? (car wf-form) 'define-workflow))
                 (parse-workflow-form (cdr wf-form))]
                [else (error 'parse-agent-form "invalid workflow form: ~a" wf-form)])))
          (kv-loop (cdr xs) purpose tools (append workflows wf-list) hooks #f)]
         [(#:hooks)
          (define h-list (flatten (car xs)))
          (kv-loop (cdr xs) purpose tools workflows (append hooks h-list) #f)]
         [else
          (kv-loop (cdr xs) purpose tools workflows hooks current-kw)])])))

(define (parse-workflow-form tail)
  (define-values (name rest) (if (null? tail) (values #f '()) (values (car tail) (cdr tail))))
  (let kv-loop ([xs rest] [triggers '()] [steps '()] [current-kw #f])
    (cond
      [(null? xs) (al-workflow (ensure-string/sym name) (reverse steps) triggers)]
      [(keyword? (car xs))
       (kv-loop (cddr xs) triggers steps (car xs))]
      [else
       (case current-kw
         [(#:triggers)
          (kv-loop (cdr xs) (flatten (car xs)) steps #f)]
         [(#:steps)
          (define step-list
            (for/list ([sf (in-list (car xs))])
              (cond
                [(and (pair? sf) (eq? (car sf) 'define-step))
                 (parse-step-form (cdr sf))]
                [else (error 'parse-workflow-form "invalid step form: ~a" sf)])))
          (kv-loop (cdr xs) triggers (append step-list steps) #f)]
         [else (kv-loop (cdr xs) triggers steps current-kw)])])))

(define (parse-step-form tail)
  (let loop ([xs tail] [id #f] [action #f] [next- #f] [cond- #t])
    (cond
      [(null? xs)
       (unless id (error 'parse-step "step missing id: ~a" tail))
       (unless action (set! action (al-atomic "noop" "__no_op__" "noop" '())))
       (al-step (ensure-string/sym id) action next- cond-)]
      [(keyword? (car xs))
       (case (car xs)
         [(#:next) (loop (cddr xs) id action (cadr xs) cond-)]
         [(#:when) (loop (cddr xs) id action next- (cadr xs))]
         [else   (loop (cddr xs) id action next- cond-)])]
      [(not id) (loop (cdr xs) (car xs) action next- cond-)]
      [(not action)
       (define a (car xs))
       (define parsed
         (cond
           [(and (pair? a) (eq? (car a) 'atomic))
            (let ([ps (cdr a)])
              (al-atomic
               (ensure-string/sym (and (pair? ps) (car ps)))
               (ensure-string/sym (and (pair? ps) (pair? (cdr ps)) (cadr ps)))
               (ensure-string/sym (and (pair? ps) (pair? (cdr ps)) (pair? (cddr ps)) (caddr ps)))
               (and (pair? ps) (pair? (cdr ps)) (pair? (cddr ps)) (cdddr ps))))]
           [else a]))
       (loop (cdr xs) id parsed next- cond-)]
      [else (loop (cdr xs) id action next- cond-)])))

(define (parse-tool-form tail)
  (define-values (name rest) (if (null? tail) (values #f '()) (values (car tail) (cdr tail))))
  (let kv-loop ([xs rest] [desc ""] [in-schema '#hash()] [out-schema '#hash()] [current-kw #f])
    (cond
      [(null? xs) (al-tool (ensure-string/sym name) desc in-schema out-schema)]
      [(keyword? (car xs))
       (kv-loop (cddr xs) desc in-schema out-schema (car xs))]
      [else
       (case current-kw
         [(#:description) (kv-loop (cdr xs) (car xs) in-schema out-schema #f)]
         [(#:input)       (kv-loop (cdr xs) desc (car xs) out-schema #f)]
         [(#:output)      (kv-loop (cdr xs) desc in-schema (car xs) #f)]
         [else            (kv-loop (cdr xs) desc in-schema out-schema current-kw)])])))

(define (parse-harness-form tail)
  (define-values (name rest) (if (null? tail) (values #f '()) (values (car tail) (cdr tail))))
  (let kv-loop ([xs rest] [base "BaseHarness"] [react '#hash((max_turns . 30))] [current-kw #f])
    (cond
      [(null? xs) (al-harness (ensure-string/sym name) base react)]
      [(keyword? (car xs))
       (kv-loop (cddr xs) base react (car xs))]
      [else
       (case current-kw
         [(#:base)  (kv-loop (cdr xs) (ensure-string/sym (car xs)) react #f)]
         [(#:react) (kv-loop (cdr xs) base (car xs) #f)]
         [else      (kv-loop (cdr xs) base react current-kw)])])))

(define (ensure-string/sym v)
  (cond
    [(symbol? v) (symbol->string v)]
    [(string? v) v]
    [else (format "~a" v)]))

(define (parse-kv tail default-name allowed-keys)
  (let loop ([xs tail]
             [name default-name]
             [acc '#hash()]
             [current-key #f])
    (cond
      [(null? xs) (values name acc)]
      [(keyword? (car xs))
       (define k (string->symbol (keyword->string (car xs))))
       (if (member k allowed-keys)
           (loop (cddr xs) name (hash-set acc k (cadr xs)) #f)
           (loop (cdr xs) name acc k))]
      [(equal? name default-name)
       (loop (cdr xs) (car xs) acc current-key)]
      [else (loop (cdr xs) name acc current-key)])))
