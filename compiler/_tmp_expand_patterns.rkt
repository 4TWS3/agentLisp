#lang racket/base
(require racket/port
         racket/file
         racket/match
         "patterns.rkt")

(define-namespace-anchor anc)
(define ns (namespace-anchor->namespace anc))

(define (expand-form form)
  (cond
    [(and (pair? form)
          (memq (car form)
                '(defreflect-agent defrouter-agent defchain-agent defparallel-agent defplanner-agent)))
     (with-handlers ([exn:fail? (lambda (e)
                                   (fprintf (current-output-port)
                                            "; EXPANDER EXCEPTION on ~a: ~a\n"
                                            (car form) (exn-message e))
                                   form)])
       (define expanded (eval form ns))
       (cond
         [(and (pair? expanded) (eq? (car expanded) 'defagent))
          (cons 'define-agent (cdr expanded))]
         [(and (pair? expanded) (eq? (car expanded) 'define-agent))
          expanded]
         [else
          (fprintf (current-output-port)
                   "; EXPANDER WARNING: ~a -> ~a (car=~a, not wrapped as define-agent/defagent)\n"
                   (car form) (if (pair? expanded) (substring (format "~s" expanded) 0 (min 60 (string-length (format "~s" expanded)))) expanded) (and (pair? expanded) (car expanded)))
          form]))]
    [else form]))

(module+ main
  (define input-file (vector-ref (current-command-line-arguments) 0))
  (define forms
    (with-handlers ([exn:fail? (lambda (e)
                                  (fprintf (current-output-port) "; READ EXCEPTION: ~a\n" (exn-message e))
                                  '())])
      (file->value-list input-file)))
  (for ([form (in-list forms)])
    (define out (expand-form form))
    (write out)
    (newline))
  (flush-output)
  (exit 0))
