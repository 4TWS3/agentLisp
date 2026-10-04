#lang racket/base

(require racket/base
         racket/cmdline
         racket/file
         racket/string
         racket/format
         "parser.rkt"
         "checker.rkt"
         "emitter.rkt")

(module+ main
  (define input-path #f)
  (define output-path #f)
  (define check-only? #f)
  (define emit-python? #t)

  (command-line
   #:program "agentlispc"
   #:once-each
   [("-i" "--input") path "Input .al source file" (set! input-path path)]
   [("-o" "--output") path "Output .py destination file (stdout if omitted)" (set! output-path path)]
   [("--check-only") "Run static checks only, do not emit" (set! check-only? #t)]
   [("--no-emit") "Alias for --check-only" (set! check-only? #t)]
   #:args positional
   (when (and (not input-path) (pair? positional))
     (set! input-path (car positional)))
   (when (and (not output-path) (> (length positional) 1))
     (set! output-path (cadr positional))))

  (unless input-path
    (fprintf (current-error-port) "agentlispc: missing input file\n")
    (fprintf (current-error-port) "usage: racket compiler/main.rkt -i INPUT.al -o OUTPUT.py [--check-only]\n")
    (exit 2))

  (define source (file->value-list input-path))
  (define ast (parse-s-exp input-path source))

  (displayln (format "==> AgentLisp v2 compiler: ~a" input-path))
  (displayln (format "    agents: ~a  tools: ~a  harnesses: ~a"
                     (length (al-ast-agents ast))
                     (length (al-ast-top-level-tools ast))
                     (length (al-ast-top-level-harnesses ast))))

  (define all-ok? (report-checks (check-ast ast)))
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
          (displayln (format "==> emitted ~a bytes -> ~a" (string-length code) output-path)))
        (display code)))

  (exit 0))

(define (file->value-list path)
  (call-with-input-file path
    (lambda (in)
      (let loop ([acc '()])
        (define v (read in))
        (if (eof-object? v)
            (reverse acc)
            (loop (cons v acc)))))))
