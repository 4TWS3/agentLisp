#lang info

(define collection "agentlisp-compiler")
(define pkg-desc "AgentLisp v2.0 Compiler - Racket frontend for Agent DSL (.al files) with static checks and Python emitter")
(define version "2.0.0a1")
(define pkg-authors '(agentlisp))

(define deps
  '("base"
    "rackunit-lib"
    "syntax/parse"
    "data-lib"
    "json-lib"
    "parser-tools-lib"))

(define build-deps
  '("racket-doc"
    "scribble-lib"))

(define test-omit-paths
  '("../examples/"))
