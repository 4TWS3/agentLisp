#lang racket/base

(require racket/port
         racket/contract
         json
         "main.rkt")

(provide (all-defined-out))

(define/contract (read-agent-file path)
  (-> path-string? any/c)
  (with-input-from-file path
    (lambda ()
      (let loop ([expr (read)]
                 [result '()])
        (if (eof-object? expr)
            (reverse result)
            (loop (read) (cons (eval expr (make-base-namespace)) result)))))))

(define/contract (agent-to-json ag [out #f])
  (->* (agent?) (output-port?) any/c)
  (let ([serialized (serialize-agent ag)])
    (if out
        (write-json serialized out)
        (jsexpr->string serialized))))

(define/contract (write-agent-json ag path)
  (-> agent? path-string? void?)
  (with-output-to-file path
    (lambda ()
      (write-json (serialize-agent ag)))
    #:exists 'replace))
