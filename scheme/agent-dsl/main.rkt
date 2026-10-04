#lang racket/base

(require racket/contract
         racket/match
         racket/string
         syntax/parse/define
         (for-syntax racket/base
                     racket/syntax))

(provide (all-defined-out))

(struct agent (name purpose tools workflows) #:transparent)
(struct tool (name description input-schema output-schema handler) #:transparent)
(struct workflow (name steps triggers) #:transparent)
(struct step (id action next condition) #:transparent)
(struct atomic-action (name target method params) #:transparent)

(define-syntax-parse-rule (define-agent name:id
                            (~optional (~seq #:purpose purpose:expr) #:defaults ([purpose #'""]))
                            (~optional (~seq #:tools (tool-def ...)) #:defaults ([(tool-def 1) '()]))
                            (~optional (~seq #:workflows (workflow-def ...)) #:defaults ([(workflow-def 1) '()])))
  #:with tools-id (format-id #'name "~a-tools" #'name)
  #:with workflows-id (format-id #'name "~a-workflows" #'name)
  (begin
    (define tools-id (list tool-def ...))
    (define workflows-id (list workflow-def ...))
    (define name
      (agent (symbol->string 'name)
             purpose
             tools-id
             workflows-id))))

(define-syntax-parse-rule (define-tool name:id
                            (~optional (~seq #:description desc:expr) #:defaults ([desc #'""]))
                            (~optional (~seq #:input input-schema:expr) #:defaults ([input-schema #'#hash()]))
                            (~optional (~seq #:output output-schema:expr) #:defaults ([output-schema #'#hash()]))
                            (~optional (~seq #:handler handler:expr) #:defaults ([handler #'#f])))
  (define name
    (tool (symbol->string 'name)
          desc
          input-schema
          output-schema
          handler)))

(define-syntax-parse-rule (define-workflow name:id
                            (~optional (~seq #:triggers triggers:expr) #:defaults ([triggers #''()]))
                            #:steps (step-def ...))
  (define name
    (workflow (symbol->string 'name)
              (list step-def ...)
              triggers)))

(define-syntax-parse-rule (define-step id:id
                            action:expr
                            (~optional (~seq #:next next:expr) #:defaults ([next #'#f]))
                            (~optional (~seq #:when condition:expr) #:defaults ([condition #'#t])))
  (define id
    (step (symbol->string 'id)
          action
          next
          condition)))

(define-syntax-parse-rule (atomic name:id target method params ...)
  (atomic-action (symbol->string 'name)
                 (symbol->string 'target)
                 (symbol->string 'method)
                 (list params ...)))

(define (validate-agent ag)
  (cond
    [(not (agent? ag)) (values #f "Not an agent struct")]
    [(string-empty? (agent-name ag)) (values #f "Agent name is empty")]
    [else
     (let loop ([tools (agent-tools ag)]
                [workflows (agent-workflows ag)])
       (cond
         [(and (null? tools) (null? workflows)) (values #t "Valid")]
         [(not (null? tools))
          (if (tool? (car tools))
              (loop (cdr tools) workflows)
              (values #f (format "Invalid tool definition: ~a" (car tools))))]
         [else
          (if (workflow? (car workflows))
              (loop tools (cdr workflows))
              (values #f (format "Invalid workflow definition: ~a" (car workflows))))]))]))

(define (serialize-agent ag)
  (when (not (agent? ag))
    (error 'serialize-agent "Expected agent struct, got: ~a" ag))
  (hasheq
   'type "agent"
   'name (agent-name ag)
   'purpose (agent-purpose ag)
   'tools (map serialize-tool (agent-tools ag))
   'workflows (map serialize-workflow (agent-workflows ag))))

(define (serialize-tool t)
  (when (not (tool? t))
    (error 'serialize-tool "Expected tool struct, got: ~a" t))
  (hasheq
   'type "tool"
   'name (tool-name t)
   'description (tool-description t)
   'input_schema (tool-input-schema t)
   'output_schema (tool-output-schema t)))

(define (serialize-workflow w)
  (when (not (workflow? w))
    (error 'serialize-workflow "Expected workflow struct, got: ~a" w))
  (hasheq
   'type "workflow"
   'name (workflow-name w)
   'triggers (workflow-triggers w)
   'steps (map serialize-step (workflow-steps w))))

(define (serialize-step s)
  (when (not (step? s))
    (error 'serialize-step "Expected step struct, got: ~a" s))
  (hasheq
   'type "step"
   'id (step-id s)
   'action (serialize-action (step-action s))
   'next (step-next s)
   'condition (step-condition s)))

(define (serialize-action act)
  (cond
    [(atomic-action? act)
     (hasheq
      'type "atomic"
      'name (atomic-action-name act)
      'target (atomic-action-target act)
      'method (atomic-action-method act)
      'params (atomic-action-params act))]
    [else act]))
