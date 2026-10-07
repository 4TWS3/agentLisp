#lang racket/base

(require racket/base
         racket/cmdline
         racket/file
         racket/string
         racket/format
         racket/pretty
         racket/port
         racket/system
         racket/path
         racket/runtime-path
         json
         "parser.rkt")

(define-runtime-path EXPANDER-PATH "_tmp_expand_patterns.rkt")
(define-runtime-path PATTERNS-PATH "patterns.rkt")

(define input-path #f)
(define output-path #f)
(define check-only? #f)
(define emit-python? #t)
(define json-errors? #f)
(define verbose? #f)
(define dump-expanded-sexp? #f)
(define dump-ast? #f)

(define (file->value-list path)
  (call-with-input-file path
    (lambda (in)
      (let loop ((acc '()))
        (define v (read in))
        (if (eof-object? v)
            (reverse acc)
            (loop (cons v acc)))))))

(define (safe-dyn mod-path sym default)
  (with-handlers ([exn:fail? (lambda (e) default)])
    (dynamic-require mod-path sym)))

(define checker-default-jsexpr-version
  (safe-dyn "checker.rkt" 'checker-default-jsexpr-version 1))
(define (exn->jsexpr e)
  ((safe-dyn "checker.rkt" 'exn->jsexpr (lambda (e) (hasheq 'message (exn-message e)))) e))
(define (exn:agentlisp:check? e)
  ((safe-dyn "checker.rkt" 'exn:agentlisp:check? (lambda (e) #f)) e))
(define (exn:agentlisp:parse? e)
  ((safe-dyn "checker.rkt" 'exn:agentlisp:parse? (lambda (e) #f)) e))
(define (exn:agentlisp:emit? e)
  ((safe-dyn "checker.rkt" 'exn:agentlisp:emit? (lambda (e) #f)) e))
(define (exn:agentlisp:check->jsexpr e)
  ((safe-dyn "checker.rkt" 'exn:agentlisp:check->jsexpr (lambda (e) (hasheq 'message (exn-message e)))) e))
(define (exn:agentlisp:check-code e)
  ((safe-dyn "checker.rkt" 'exn:agentlisp:check-code (lambda (e) 'UNKNOWN_CHECK_ERROR)) e))
(define (exn:agentlisp:parse-code e)
  ((safe-dyn "checker.rkt" 'exn:agentlisp:parse-code (lambda (e) 'UNKNOWN_PARSE_ERROR)) e))
(define (to-str v)
  ((safe-dyn "checker.rkt" 'to-str (lambda (v) (if (symbol? v) (symbol->string v) (format "~a" v)))) v))
(define (with-srcloc-from-form src proc)
  ((safe-dyn "checker.rkt" 'with-srcloc-from-form (lambda (src proc) (proc))) src proc))
(define (parse-defagent form)
  ((safe-dyn "agentlisp_compiler.rkt" 'parse-defagent (lambda (form) #f)) form))
(define (check-agent parsed)
  ((safe-dyn "agentlisp_compiler.rkt" 'check-agent (lambda (parsed) (void))) parsed))
(define (current-checker-source-name)
  ((safe-dyn "agentlisp_compiler.rkt" 'current-checker-source-name (lambda () "unknown"))))
(define (emit-python ast mod-name)
  ((safe-dyn "emitter.rkt" 'emit-python (lambda (a m) "# generated (emitter not loaded)\n")) ast mod-name))

(define (emit-json-errors errs)
  (write-json errs (current-output-port))
  (newline)
  (flush-output (current-output-port)))

(define (expand-pattern-macros/via-subprocess all-forms)
  (with-handlers ([exn:fail? (lambda (e)
                                (fprintf (current-error-port) "; expand-pattern-macros IN-PROCESS EXCEPTION: ~a\n" (exn-message e))
                                all-forms)])
    (define ns (make-base-namespace))
    (eval `(require (file ,(path->string PATTERNS-PATH))) ns)
    (parameterize ((current-namespace ns))
      (for/list ((form (in-list all-forms)))
        (define expanded (eval form))
        (cond
          [(and (pair? expanded) (eq? (car expanded) 'defagent))
           (cons 'define-agent (cdr expanded))]
          [else expanded])))))

(define (check-ast/legacy a expanded-source input-path)
  (with-handlers ((exn:agentlisp:check?
                   (lambda (e)
                     (define j (exn:agentlisp:check->jsexpr e))
                     (list (hasheq 'ok? #f
                                   'title (symbol->string (exn:agentlisp:check-code e))
                                   'message (exn-message e)
                                   'jsexpr j))))
                  (exn:agentlisp:parse?
                   (lambda (e)
                     (define j (exn->jsexpr e))
                     (list (hasheq 'ok? #f
                                   'title (symbol->string (exn:agentlisp:parse-code e))
                                   'message (exn-message e)
                                   'jsexpr j)))))
    (define agents (al-ast-agents a))
    (cond
      ((pair? agents)
       (define combined-results
         (for/list ((ag-form expanded-source)
                    #:when (and (pair? ag-form) (eq? (car ag-form) 'define-agent)))
           (with-handlers ((exn:agentlisp:check?
                            (lambda (e)
                              (hasheq 'ok? #f
                                      'title (symbol->string (exn:agentlisp:check-code e))
                                      'message (exn-message e)
                                      'jsexpr (exn:agentlisp:check->jsexpr e)))))
             (define-values (parsed-name parsed-acc)
               (let loop ((xs (cdr ag-form)) (name (if (pair? (cdr ag-form)) (cadr ag-form) #f)))
                 (values (and name (to-str name)) #t)))
             (with-srcloc-from-form
              input-path
              (lambda ()
                (let ((parsed (parse-defagent ag-form)))
                  (check-agent parsed)
                  (hasheq 'ok? #t 'title (format "check-agent: ~a" (or parsed-name "anon")) 'message "")))))))
       combined-results)
      (else
       (list (hasheq 'ok? #t 'title "empty-ast" 'message "no define-agent forms, trivially pass static checks"))))))

(define (report-checks results)
  (define bad (for/list ((r results) #:unless (hash-ref r 'ok? #f)) r))
  (cond
    ((pair? bad)
     (when (not json-errors?)
       (for ((b bad))
         (fprintf (current-error-port)
                  "  (CHECK FAILED) ~a: ~a\n"
                  (hash-ref b 'title "?")
                  (hash-ref b 'message ""))))
     #f)
    (else #t)))

(with-handlers ([exn:fail? (lambda (e) (void))])
  (dynamic-require "checker.rkt" #f))
(with-handlers ([exn:fail? (lambda (e) (void))])
  (dynamic-require "emitter.rkt" #f))
(with-handlers ([exn:fail? (lambda (e) (void))])
  (dynamic-require "agentlisp_compiler.rkt" #f))

(command-line
 #:program "agentlispc"
 #:once-each
 (("-i" "--input") path "Input .al source file" (set! input-path path))
 (("-o" "--output") path "Output .py destination file (stdout if omitted)" (set! output-path path))
 (("--check-only") "Run static checks only, do not emit" (set! check-only? #t))
 (("--no-emit") "Alias for --check-only" (set! check-only? #t))
 (("--json-errors") "Emit compiler diagnostics as JSON array to stdout (SRS §5.1, 用于 IDE 红波浪)"
  (set! json-errors? #t))
 (("-v" "--verbose") "Verbose: print progress" (set! verbose? #t))
 (("--dump-expanded-sexp") "Dump post-pattern-expansion s-expressions, then exit"
  (set! dump-expanded-sexp? #t))
 (("--dump-ast") "Alias for --dump-expanded-sexp"
  (set! dump-expanded-sexp? #t)
  (set! dump-ast? #t))
 #:args positional
 (when (and (not input-path) (pair? positional))
   (set! input-path (car positional)))
 (when (and (not output-path) (> (length positional) 1))
   (set! output-path (cadr positional))))

(unless input-path
  (when json-errors?
    (write-json
     (list (hasheq 'schema_version checker-default-jsexpr-version
                   'code           "CLI_MISSING_INPUT"
                   'severity       "error"
                   'srs_id         ""
                   'message        "agentlispc: missing input file"
                   'agent_name     'null
                   'srcloc         (hasheq 'source "command-line"
                                           'line     'null 'column 'null
                                           'position 'null 'span 'null)
                   'hints          '("usage: racket compiler/main.rkt -i INPUT.al -o OUTPUT.py (--check-only) (--json-errors)")))
     (current-output-port))
    (newline))
  (fprintf (current-error-port) "agentlispc: missing input file\n")
  (fprintf (current-error-port) "usage: racket compiler/main.rkt -i INPUT.al -o OUTPUT.py (--check-only) (--json-errors)\n")
  (exit 2))

(define source
  (with-handlers ((exn:fail?
                   (lambda (e)
                     (if json-errors?
                         (begin
                           (emit-json-errors
                            (list
                             (hasheq 'schema_version checker-default-jsexpr-version
                                     'code           "IO_READ_FAILED"
                                     'severity       "error"
                                     'srs_id         ""
                                     'message        (exn-message e)
                                     'agent_name     'null
                                     'srcloc         (hasheq 'source (or input-path "unknown")
                                                             'line 'null 'column 'null
                                                             'position 'null 'span 'null)
                                     'hints          '("检查文件存在性与权限；路径必须是 UTF-8"))))
                           (exit 3))
                         (raise e)))))
    (file->value-list input-path)))

(define expanded-source
  (expand-pattern-macros/via-subprocess source))

(when dump-expanded-sexp?
  (for ((form (in-list expanded-source)))
    (displayln (format "~s" form)))
  (exit 0))

(define ast
  (with-handlers
    (((lambda (e) (or (exn:agentlisp:parse? e) (exn:fail:read? e) (exn:fail? e)))
      (lambda (e)
        (cond
          (json-errors?
           (emit-json-errors (list (exn->jsexpr e)))
           (exit 2))
          (else (raise e))))))
    (with-srcloc-from-form input-path (parse-s-exp input-path expanded-source))))

(when verbose?
  (displayln (format "==> AgentLisp v2 compiler: ~a" input-path))
  (displayln (format "    agents: ~a  tools: ~a  harnesses: ~a"
                     (length (al-ast-agents ast))
                     (length (al-ast-top-level-tools ast))
                     (length (al-ast-top-level-harnesses ast)))))

(define check-results
  (with-handlers
    (((lambda (e) #t)
      (lambda (e)
        (cond
          (json-errors?
           (emit-json-errors (list (exn->jsexpr e)))
           (exit 1))
          (else
           (list (hasheq 'ok? #f 'title (format "~a" (if (exn? e) (exn-message e) e))
                         'message (format "~a" (if (exn? e) (exn-message e) e)))))))))
    (let loop ((xs expanded-source) (errs-rev '()))
      (cond
        ((null? xs) (reverse errs-rev))
        (else
         (define form (car xs))
         (cond
           ((and (pair? form) (eq? (car form) 'define-agent))
            (let inner ()
              (dynamic-require '(submod "." json-errors-runner) #f)
              (with-handlers ((exn:agentlisp:check?
                               (lambda (e)
                                 (loop (cdr xs)
                                       (cons (hasheq 'ok? #f
                                                     'title (symbol->string (exn:agentlisp:check-code e))
                                                     'message (exn-message e)
                                                     'jsexpr (exn:agentlisp:check->jsexpr e))
                                             errs-rev))))
                                (exn:agentlisp:parse?
                                 (lambda (e)
                                   (loop (cdr xs)
                                         (cons (hasheq 'ok? #f
                                                       'title (symbol->string (exn:agentlisp:parse-code e))
                                                       'message (exn-message e)
                                                       'jsexpr (exn->jsexpr e))
                                               errs-rev))))
                                (exn:fail?
                                 (lambda (e)
                                   (loop (cdr xs)
                                         (cons (hasheq 'ok? #f
                                                       'title "RUNTIME_CHECK_EXN"
                                                       'message (exn-message e)
                                                       'jsexpr (exn->jsexpr e))
                                               errs-rev)))))
                (let ((parsed (parameterize ((current-checker-source-name input-path))
                                 (let ((p (parse-defagent form)))
                                   (check-agent p)
                                   p)))
                      (aname
                       (if (and (pair? (cdr form)) (pair? (cddr form)))
                           (to-str (cadr form))
                           "anon")))
                  (loop (cdr xs)
                      (cons (hasheq 'ok? #t
                                    'title (format "check-agent: ~a" aname)
                                    'message "")
                            errs-rev))))))
           (else (loop (cdr xs) errs-rev))))))))

(when json-errors?
  (define json-list
    (for/fold ((acc '()))
              ((r (in-list check-results)))
      (cond
        ((not (hash-ref r 'ok? #f))
         (define js (hash-ref r 'jsexpr (lambda () (exn->jsexpr (make-exn:fail (hash-ref r 'message "?") (current-continuation-marks))))))
         (append acc (list js)))
        (else acc))))
  (emit-json-errors json-list)
  (when (pair? json-list)
    (exit 1))
  (when check-only?
    (exit 0)))

(define all-ok? (report-checks check-results))
(unless all-ok?
  (fprintf (current-error-port) "\nstatic checks FAILED, aborting.\n")
  (exit 1))

(when check-only?
  (displayln "static checks PASSED (check-only mode).")
  (exit 0))

(when emit-python?
  (define module-name (if output-path
                          (path->string (path-replace-extension (file-name-from-path output-path) #""))
                          "generated_agent"))
  (define code (emit-python ast module-name))
  (if output-path
      (begin
        (make-parent-directory* output-path)
        (display-to-file code output-path #:exists 'replace)
        (when verbose?
          (displayln (format "==> emitted ~a bytes -> ~a" (string-length code) output-path))))
      (display code)))

(exit 0)

(module+ json-errors-runner
  (void))
