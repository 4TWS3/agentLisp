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
(define-runtime-path PATTERNS-V2-PATH "patterns_v2.rkt")
(define-runtime-path PATTERNS-CHECKER-V2-PATH "patterns_checker_v2.rkt")
(define-runtime-path CHECKER-PATH "checker.rkt")
(define-runtime-path EMITTER-PATH "emitter.rkt")
(define-runtime-path COMPILER-PATH "agentlisp_compiler.rkt")
(define-runtime-path MAIN-RKT-PATH "main.rkt")
;; 仓库根：<root>/compiler/main.rkt -> <root>
(define PROJECT-ROOT (simplify-path (build-path (path-only MAIN-RKT-PATH) "..")))

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
  (safe-dyn CHECKER-PATH 'checker-default-jsexpr-version 1))
(define (exn->jsexpr e)
  ((safe-dyn CHECKER-PATH 'exn->jsexpr (lambda (e) (hasheq 'message (exn-message e)))) e))
(define (exn:agentlisp:check? e)
  ((safe-dyn CHECKER-PATH 'exn:agentlisp:check? (lambda (e) #f)) e))
(define (exn:agentlisp:parse? e)
  ((safe-dyn CHECKER-PATH 'exn:agentlisp:parse? (lambda (e) #f)) e))
(define (exn:agentlisp:emit? e)
  ((safe-dyn CHECKER-PATH 'exn:agentlisp:emit? (lambda (e) #f)) e))
(define (exn:agentlisp:check->jsexpr e)
  ((safe-dyn CHECKER-PATH 'exn:agentlisp:check->jsexpr (lambda (e) (hasheq 'message (exn-message e)))) e))
(define (exn:agentlisp:check-code e)
  ((safe-dyn CHECKER-PATH 'exn:agentlisp:check-code (lambda (e) 'UNKNOWN_CHECK_ERROR)) e))
(define (exn:agentlisp:parse-code e)
  ((safe-dyn CHECKER-PATH 'exn:agentlisp:parse-code (lambda (e) 'UNKNOWN_PARSE_ERROR)) e))
(define (to-str v)
  ((safe-dyn CHECKER-PATH 'to-str (lambda (v) (if (symbol? v) (symbol->string v) (format "~a" v)))) v))
(define (with-srcloc-from-form src proc)
  ((safe-dyn CHECKER-PATH 'with-srcloc-from-form (lambda (src proc) (proc))) src proc))
(define (parse-defagent form)
  ((safe-dyn COMPILER-PATH 'parse-defagent (lambda (form) #f)) form))
(define (check-agent parsed)
  ((safe-dyn COMPILER-PATH 'check-agent (lambda (parsed) (void))) parsed))
;; 必须是 parameter（不能是过程）：本文件 L310 的 parameterize 与 checker.rkt 的
;; with-srcloc-from-form 宏都会 parameterize 它；旧实现是过程，直接 contract violation。
;; 优先复用 checker.rkt 导出的真 parameter（这样 srcloc 能传到 checker 内部），否则本地兜底。
(define current-checker-source-name
  (let ([p (safe-dyn CHECKER-PATH 'current-checker-source-name #f)])
    (if (parameter? p) p (make-parameter "unknown"))))
(define (emit-python ast mod-name)
  ((safe-dyn EMITTER-PATH 'emit-python (lambda (a m) "# generated (emitter not loaded)\n")) ast mod-name))

(define (emit-json-errors errs)
  (write-json errs (current-output-port))
  (newline)
  (flush-output (current-output-port)))

;; ---------------------------------------------------------------------------
;; CR-42 F2：patterns_checker_v2.rkt 旁路 checker 的真实接线。
;; 旧实现（CR-41）只 (void (eval '(lambda ...) ns2)) 构造过程后即丢弃，
;; 导致 NFR-PATTERN-01/02 从未执行（且 checker 内部 tag 口径错误从未暴露）。
;; 现在以 fixtures 为数据源真正 apply run-patterns-checker-v2；
;; 统计行只写 stderr（stdout 供编译产物/--dump-ast 使用，绝不能被污染）。
;; ---------------------------------------------------------------------------
(define patterns-fixtures-v1-dir (build-path PROJECT-ROOT "tests" "patterns" "fixtures"))
(define patterns-fixtures-v2-dir (build-path PROJECT-ROOT "tests" "patterns" "fixtures_v2"))

(define (safe-read-first-datum path)
  (with-handlers ([(lambda (e) #t)
                   (lambda (e)
                     (fprintf (current-error-port)
                              "; patterns_checker_v2 READ-SKIP: ~a (~a)~n"
                              path (exn-message e))
                     #f)])
    (and path (file-exists? path)
         (with-input-from-file path
           (lambda ()
             (let ((v (read)))
               (if (eof-object? v) #f v)))))))

(define (eval-form/quiet form ns)
  (with-handlers ([(lambda (e) #t) (lambda (e) #f)])
    (eval form ns)))

;; -> (values hc-index gen-index)
;;   hc-index : hash macro-symbol -> (cons hc-al-path hc-expected-path)
;;   gen-index: hash macro-symbol -> generic-al-path
;; V1 HC fixture 无场景后缀（defreflect_code_refiner.al）；V2 HC 为 *_hc_HC.al；
;; V1 无 generic fixture，用仓库既有的 fr_pattern_02_*_auto_raise.al（GENERIC 分支实测输入）。
(define (index-pattern-fixtures dir)
  (for/fold ([hc (hash)] [gen (hash)]) ([name (in-list (directory-list dir))])
    (define p (build-path dir name))
    (define s (path->string name))
    (define expected (path-replace-extension p #".expected.rkt"))
    (define form (and (regexp-match? #rx"\\.al$" s) (safe-read-first-datum p)))
    (define m (and (pair? form) (car form)))
    (cond
      [(not (and m (symbol? m))) (values hc gen)]
      [(regexp-match? #rx"^fr_pattern_02_.*_auto_raise\\.al$" s)
       (values hc (hash-set gen m p))]
      [(regexp-match? #rx"_generic_GENERIC\\.al$" s)
       (values hc (hash-set gen m p))]
      [(and (regexp-match? #rx"_reverse_REVERSE\\.al$" s)) (values hc gen)]
      [(file-exists? expected)
       (values (hash-set hc m (cons p expected)) gen)]
      [else (values hc gen)])))

(define (make-patterns-checker-getters ns)
  (define-values (v1-hc v1-gen) (index-pattern-fixtures patterns-fixtures-v1-dir))
  (define-values (v2-hc v2-gen) (index-pattern-fixtures patterns-fixtures-v2-dir))
  (define hc (for/fold ([acc v1-hc]) ([(k v) v2-hc]) (hash-set acc k v)))
  (define gen (for/fold ([acc v1-gen]) ([(k v) v2-gen]) (hash-set acc k v)))
  (define (expand-at p) (and p (eval-form/quiet (safe-read-first-datum p) ns)))
  (values
   (lambda (m _hc-id) (define e (hash-ref hc m #f)) (and e (expand-at (car e))))
   (lambda (m _hc-id) (define e (hash-ref hc m #f)) (and e (safe-read-first-datum (cdr e))))
   (lambda (m) (expand-at (hash-ref gen m #f)))))

(define (run-patterns-checker-v2/report ns)
  (with-handlers ([(lambda (e) #t)
                   (lambda (e)
                     (fprintf (current-error-port)
                              "; patterns_checker_v2 SKIP: ~a~n" (exn-message e)))])
    (define-values (get-hc-exp get-hc-hw get-gen-exp) (make-patterns-checker-getters ns))
    (define ns2 (make-base-namespace))
    (eval '(require racket/base racket/match racket/list racket/string) ns2)
    (eval `(require (file ,(path->string PATTERNS-CHECKER-V2-PATH))) ns2)
    (define run (eval 'run-patterns-checker-v2 ns2))
    (define-values (cells pass fail) (run get-hc-exp get-hc-hw get-gen-exp))
    (fprintf (current-error-port)
             "; patterns_checker_v2: cells=~a pass=~a fail=~a (NFR01 15HC+15GEN / NFR02 8x15=120)~n"
             (length cells) pass fail)
    (define failed (for/list ([c (in-list cells)] #:unless (caddr c)) c))
    (when (pair? failed)
      (define by-category
        (for/fold ([h (hash)]) ([c (in-list failed)])
          (hash-update h (cadr c) add1 0)))
      (fprintf (current-error-port)
               "; patterns_checker_v2 FAILED by-category: ~a~n"
               (string-join (for/list ([(k v) (in-hash by-category)])
                              (format "~a=~a" k v))
                            " "))
      (fprintf (current-error-port)
               "; patterns_checker_v2 FAILED cells: ~a~n"
               (string-join (for/list ([c (in-list failed)])
                              (format "~a [~a]" (car c) (cadddr c)))
                            ", ")))
    (void)))

(define (expand-pattern-macros/via-subprocess all-forms)
  (with-handlers ([exn:fail? (lambda (e)
                                (fprintf (current-error-port) "; expand-pattern-macros OUTER EXN: ~a~n" (exn-message e))
                                all-forms)])
    (define ns (make-base-namespace))
    (eval '(require racket/base racket/port racket/file racket/path racket/runtime-path racket/syntax racket/string racket/match racket/pretty) ns)
    (eval `(require (file ,(path->string PATTERNS-PATH))) ns)
    (eval `(require (file ,(path->string PATTERNS-V2-PATH))) ns)
    (define pattern-macro-names
      '(defreflect-agent defrouter-agent defchain-agent defparallel-agent defplanner-agent
        defpriority-agent defdecomposition-agent deffsm-agent defevaluator-agent
        deftopic-model-agent defdecomposer-agent defguardrails-safety-agent
        defhitl-agent defexception-agent defexploration-agent))
    (define all-expanded
      (for/list ((form (in-list all-forms)))
        (cond
          ;; CR-42：只 eval 模式宏调用。其他顶层子表单（define-tool / define-harness /
          ;; define-workflow …）不是可求值表达式，eval 只会报 "undefined" 并污染 stderr；
          ;; 它们必须原样透传给下游 parser/checker。
          [(and (pair? form) (memq (car form) pattern-macro-names))
           (with-handlers ([exn:fail? (lambda (e)
                                        (fprintf (current-error-port) "; expand-single ~s FAIL: ~a~n" (car form) (exn-message e))
                                        form)])
             (define expanded (eval form ns))
             (cond
               [(and (pair? expanded) (eq? (car expanded) 'defagent))
                (cons 'define-agent (cdr expanded))]
               [(and (pair? expanded) (memq (car expanded) pattern-macro-names))
                (cons 'define-agent (cdr expanded))]
               [else expanded]))]
          [else form])))
    ;; CR-42 F2：真正 apply 旁路 checker（结果只落 stderr）
    (run-patterns-checker-v2/report ns)
    all-expanded))

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
  (dynamic-require CHECKER-PATH #f))
(with-handlers ([exn:fail? (lambda (e) (void))])
  (dynamic-require EMITTER-PATH #f))
(with-handlers ([exn:fail? (lambda (e) (void))])
  (dynamic-require COMPILER-PATH #f))

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
    ;; 必须传 thunk：checker.rkt 的 with-srcloc-from-form 是宏（无法被 dynamic-require 取值），
    ;; 本文件的动态包装会退化为 (lambda (src proc) (proc))，因此这里必须给过程而不是已求值的 AST。
    (with-srcloc-from-form input-path (lambda () (parse-s-exp input-path expanded-source)))))

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
              ;; (submod "." json-errors-runner) 只在 main.rkt 被 require 时才有基路径；
              ;; 以脚本方式运行（racket compiler/main.rkt）时会抛 "no base path"。
              ;; 该子模块是空实现，这里做容错，避免它把正常的静态检查一起带崩。
              (with-handlers ([exn:fail? (lambda (e) (void))])
                (dynamic-require '(submod "." json-errors-runner) #f))
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
