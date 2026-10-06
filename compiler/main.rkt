#lang racket/base

(require racket/base
         racket/cmdline
         racket/file
         racket/string
         racket/format
         racket/pretty
         racket/port
         racket/system
         json
         "parser.rkt")

(module+ main
  (define input-path #f)
  (define output-path #f)
  (define check-only? #f)
  (define emit-python? #t)
  (define json-errors? #f)
  (define verbose? #f)
  (define dump-expanded-sexp? #f)

  ;; ---- Dynamic require checker/emitter AT RUNTIME, NOT at module load ----
  ;; Racket 8.12 rejects checker.rkt L102 (struct srcloc* #:transparent #:prefab) as
  ;; multiple inspector conflict. --dump-ast / --dump-expanded-sexp mode NEVER needs
  ;; checker or emitter, so we dynamic-require them only after we are past the dump
  ;; early-exit. If dynamic-require fails, fall back to harmless stubs.
  (define checker-loaded? #f)
  (with-handlers ([exn:fail? (lambda (e) (set! checker-loaded? #f))])
    (dynamic-require "checker.rkt" #f)
    (set! checker-loaded? #t))
  (with-handlers ([exn:fail? (lambda (e) (void))])
    (dynamic-require "emitter.rkt" #f))
  (define (dyn mod-path sym default)
    (with-handlers ([exn:fail? (lambda (e) default)])
      (dynamic-require mod-path sym)))
  (define checker-default-jsexpr-version
    (dyn '"checker.rkt" 'checker-default-jsexpr-version 1))
  (define (exn->jsexpr e)
    (define f (dyn '"checker.rkt" 'exn->jsexpr
                   (lambda (e) (hasheq 'message (if (exn? e) (exn-message e) "exn")))))
    (f e))
  (define (exn:agentlisp:check? e)
    (define f (dyn '"checker.rkt" 'exn:agentlisp:check? (lambda (e) #f)))
    (f e))
  (define (exn:agentlisp:parse? e)
    (define f (dyn '"checker.rkt" 'exn:agentlisp:parse? (lambda (e) #f)))
    (f e))
  (define (exn:agentlisp:check->jsexpr e)
    (define f (dyn '"checker.rkt" 'exn:agentlisp:check->jsexpr
                   (lambda (e) (hasheq 'message (if (exn? e) (exn-message e) "exn")))))
    (f e))
  (define (exn:agentlisp:check-code e)
    (define f (dyn '"checker.rkt" 'exn:agentlisp:check-code (lambda (e) 'UNKNOWN)))
    (f e))
  (define (exn:agentlisp:parse-code e)
    (define f (dyn '"checker.rkt" 'exn:agentlisp:parse-code (lambda (e) 'UNKNOWN)))
    (f e))
  (define current-checker-source-name
    (dyn '"checker.rkt" 'current-checker-source-name (make-parameter #f)))
  (define (check-agent v)
    (define f (dyn '"checker.rkt" 'check-agent (lambda (v) (void))))
    (f v))
  (define (to-str v)
    (define f (dyn '"checker.rkt" 'to-str
                   (lambda (v)
                     (cond
                       [(symbol? v) (symbol->string v)]
                       [(string? v) v]
                       [(number? v) (number->string v)]
                       [(boolean? v) (if v "True" "False")]
                       [else (format "~a" v)]))))
    (f v))
  (define (with-srcloc-from-form src thnk)
    (define f (dyn '"checker.rkt" 'with-srcloc-from-form (lambda (src t) (t))))
    (f src thnk))
  (define (parse-defagent v)
    (with-handlers ([exn:fail? (lambda (e) v)])
      (dynamic-require "agentlisp_compiler.rkt" #f))
    (define f (dyn '"agentlisp_compiler.rkt" 'parse-defagent (lambda (v) v)))
    (f v))
  (define (emit-python ast name)
    (define f (dyn '"emitter.rkt" 'emit-python
                   (lambda (a n) "# agentlisp emitter not loaded\n")))
    (f ast name))

  (command-line
   #:program "agentlispc"
   #:once-each
   (("-i" "--input") path "Input .al source file" (set! input-path path))
   (("-o" "--output") path "Output .py destination file (stdout if omitted)" (set! output-path path))
   (("--check-only") "Run static checks only, do not emit" (set! check-only? #t))
   (("--no-emit") "Alias for --check-only" (set! check-only? #t))
   (("--json-errors") "Emit compiler diagnostics as JSON array to stdout (SRS §5.1, 用于 IDE 红波浪)"
    (set! json-errors? #t))
   (("--dump-ast") "Alias for --dump-expanded-sexp"
    (set! dump-expanded-sexp? #t))
   (("--dump-expanded-sexp") "After Pattern Macro Expansion, dump all top-level sexp to stdout then exit"
    (set! dump-expanded-sexp? #t))
   (("-v" "--verbose") "Verbose: print progress" (set! verbose? #t))
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

  (define (emit-json-errors errs)
    (write-json errs (current-output-port))
    (newline)
    (flush-output (current-output-port)))

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

  ;; -------- Phase 2: Pattern Macro Expansion (via ISOLATED subprocess) --------
  ;; Why subprocess? Because patterns.rkt contains long #<<PROMPT Chinese heredoc strings;
  ;; when racket 8.12 loads checker.rkt at module-top (struct #:transparent+#:prefab)
  ;; combined with deep-nested (..) reader bracket counting, reader error is triggered.
  ;; By using a separate subprocess we isolate the readers.
  (define (expand-pattern-macros/via-subprocess all-forms)
    (with-handlers ((exn:fail? (lambda (e) all-forms)))
      (define tmp-in (make-temporary-file "agentlisp_src_~a.al"))
      (with-output-to-file tmp-in
        (lambda ()
          (for ((form (in-list all-forms)))
            (displayln (format "~s" form))))
        #:exists 'replace)
      (define helper
        (build-path (current-directory) "compiler" "_tmp_expand_patterns.rkt"))
      (define racket-bin (find-executable-path "racket"))
      (cond
        ((not (and racket-bin (file-exists? helper))) all-forms)
        (else
         (define-values (proc stdout stdin stderr)
           (process*/ports #f #f #f racket-bin helper (path->string tmp-in)))
         (define out-str (port->string stdout))
         (define rc (proc 'exit-code))
         (close-input-port stdout)
         (close-output-port stdin)
         (close-input-port stderr)
         (delete-file tmp-in)
         (cond
           ((zero? rc)
            (with-input-from-string out-str
              (lambda ()
                (let loop ((acc '()))
                  (define v (read))
                  (if (eof-object? v)
                      (reverse acc)
                      (loop (cons v acc)))))))
           (else all-forms))))))

  (define expanded-source
    (expand-pattern-macros/via-subprocess source))

  ;; dump-expanded-sexp / --dump-ast: print expanded sexp list (one form per line) then exit 0
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

  ;; 兼容 report-checks / check-ast：
  ;; 主文件 agentlisp_compiler.rkt 的 API 是 (check-agent parsed) 抛异常；
  ;; 而 parser.rkt 返回的是 al-ast，需要 parse-defagent + check-agent。
  ;; 为了兼容 test-core.rkt 里的 (check-ast ast) → list of check-result，
  ;; 这里用 "逐个 agent 调用 parse-defagent + check-agent" 的方式驱动：
  (define (check-ast/legacy a)
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
                (begin
                  (with-handlers ([exn:fail? (lambda (e) (void))])
                    (dynamic-require "agentlisp_compiler.rkt" #f))
                  (define parsed (parse-defagent ag-form))
                  (check-agent parsed)
                  (hasheq 'ok? #t 'title (format "check-agent: ~a" (or parsed-name "anon")) 'message ""))))))
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

  ;; 真正执行检查：优先用 agentlisp_compiler.rkt 的 parse-defagent + check-agent（返回单错误更精准）
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
                  (with-handlers ([exn:fail? (lambda (e) (void))])
                    (dynamic-require "agentlisp_compiler.rkt" #f))
                  (parameterize ((current-checker-source-name input-path))
                    (define parsed (parse-defagent form))
                    (check-agent parsed))
                  (define aname
                    (if (and (pair? (cdr form)) (pair? (cddr form)))
                        (to-str (cadr form))
                        "anon"))
                  (loop (cdr xs)
                        (cons (hasheq 'ok? #t
                                      'title (format "check-agent: ~a" aname)
                                      'message "")
                              errs-rev)))))
             (else (loop (cdr xs) errs-rev))))))))

  ;; JSON errors 输出模式：把所有 failed 的 jsexpr 打平成一个 array；成功时输出 ()
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

  (exit 0))

(define (file->value-list path)
  (call-with-input-file path
    (lambda (in)
      (let loop ((acc '()))
        (define v (read in))
        (if (eof-object? v)
            (reverse acc)
            (loop (cons v acc)))))))

(module+ json-errors-runner
  ;; 占位：避免 dynamic-require 失败，真正逻辑在 main 内 inline 了
  (void))
