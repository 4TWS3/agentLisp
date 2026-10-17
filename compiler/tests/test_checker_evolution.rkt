#lang racket/base
;; FR-EVO-2（US-47）：突变目标侵入不可变不变量 -> ERR_IMMUTABLE_INVARIANT_VIOLATION
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

(test-case "target intruding invariant raises ERR_IMMUTABLE_INVARIANT_VIOLATION"
  (check-exn
   (lambda (e) (regexp-match? #rx"ERR_IMMUTABLE_INVARIANT_VIOLATION" (exn-message e)))
   (lambda ()
     (parse-defagent
      (mk-evo '(:evolution
                :mutation-targets (skills kv-alignment)
                :immutable-invariants (kv-alignment workspace-root forbidden-commands)
                :verifier-gate (:suite "t2" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05)))))))

(test-case "disjoint target/invariant does not raise"
  (check-not-exn
   (lambda ()
     (parse-defagent
      (mk-evo '(:evolution
                :mutation-targets (skills)
                :immutable-invariants (kv-alignment workspace-root forbidden-commands)
                :verifier-gate (:suite "t2" :min-pass-rate 0.9 :mcnemar-p-threshold 0.05)))))))
