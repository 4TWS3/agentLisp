#lang racket/base
(require racket/port
         racket/file
         racket/match
         "patterns.rkt")

(module+ main
  (define input-file (vector-ref (current-command-line-arguments) 0))
  (define forms
    (with-handlers ([exn:fail? (lambda (e) (exit 2))])
      (file->value-list input-file)))
  (define (expand-one form)
    (cond
      [(and (pair? form)
            (memq (car form)
                  '(defreflect-agent defrouter-agent defchain-agent defparallel-agent defplanner-agent)))
       (with-handlers ([exn:fail? (lambda (e) form)])
         (define expanded (eval form (make-base-empty-namespace)))
         (cond
           [(and (pair? expanded) (eq? (car expanded) 'defagent))
            (cons 'define-agent (cdr expanded))]
           [else form]))]
      [else form]))
  ;; NOTE: above ns is empty (no bindings) so eval will FAIL.
  ;; We use correct ns via require above:
  (define-namespace-anchor anc)
  (define ns (namespace-anchor->namespace anc))
  (for ([form (in-list forms)])
    (define out
      (cond
        [(and (pair? form)
              (memq (car form)
                    '(defreflect-agent defrouter-agent defchain-agent defparallel-agent defplanner-agent)))
         (with-handlers ([exn:fail? (lambda (e) form)])
           (define expanded (eval form ns))
           (cond
             [(and (pair? expanded) (eq? (car expanded) 'defagent))
              (cons 'define-agent (cdr expanded))]
             [else form]))]
        [else form]))
    (displayln (format "~s" out)))
  (exit 0))
