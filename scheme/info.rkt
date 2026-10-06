#lang info

(define collection "agent-dsl")
(define pkg-desc "Agent DSL - A Scheme-based Domain Specific Language for defining intelligent agent behaviors")
(define version "0.1.0")
(define pkg-authors '(agentlisp))

(define deps
  '("rackunit-lib"
    "data-lib"))

(define build-deps
  '("racket-doc"
    "scribble-lib"))

(define scribblings
  '(("scribblings/agent-dsl.scrbl" ())))

(define test-omit-paths
  '("examples/"))
