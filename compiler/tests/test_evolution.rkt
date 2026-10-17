#lang racket/base
;; FR-EVO-1（US-47）：parse-defagent 解析 (:evolution ...) 并返回结构化 AST。
(require rackunit
         (file "../agentlisp_compiler.rkt"))

(define (mk-evo blk)
  `(define-agent g
     (:model :provider "anthropic" :name "m" :system-prompt "s")
     (:tools (import-builtin bash))
     (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
     (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
               (:verify :json-schema #t)
               (:correct :max-retries 2 :on-failure abort))
     ,blk))

(test-case "keyword form parses into structured AST"
  (define p
    (parse-defagent
     (mk-evo '(:evolution
               :online-trace #t
               :offline-evolver "meta-diagnosis-agent"
               :mutation-targets (skills prompt-patches)
               :immutable-invariants (kv-alignment workspace-root forbidden-commands model-provider)
               :verifier-gate (:suite "t2-bench@v1.0" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05)))))
  (define e (hash-ref p 'evolution))
  (check-true (hash-ref e 'online-trace))
  (check-equal? (hash-ref e 'offline-evolver) "meta-diagnosis-agent")
  (check-equal? (hash-ref e 'mutation-targets) '(:skills :prompt-patches))
  (check-equal? (hash-ref e 'immutable-invariants)
                '(:kv-alignment :workspace-root :forbidden-commands :model-provider))
  (check-equal? (hash-ref (hash-ref e 'verifier-gate) 'name) "t2-bench@v1.0"))

(test-case "positional form still parses"
  (define p
    (parse-defagent
     (mk-evo '(:evolution
               (:mutation-targets :skills)
               (:immutable-invariants :kv-alignment :workspace-root :forbidden-commands)
               (:verifier-gate "t2-bench@v1.0" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05)))))
  (define e (hash-ref p 'evolution))
  (check-false (hash-ref e 'online-trace))
  (check-equal? (hash-ref e 'mutation-targets) '(:skills)))
