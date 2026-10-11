#lang info

(define collection "agentlisp-compiler")
(define pkg-desc "AgentLisp v2.0 Compiler - Racket frontend for Agent DSL (.al files) with static checks and Python emitter")
(define version "2.0.0a1")
(define pkg-authors '(agentlisp))

(define deps
  '("base"))

(define build-deps
  '("racket-doc"
    "scribble-lib"))

(define test-omit-paths
  '("../examples/"))
