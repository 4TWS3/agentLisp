#lang racket/base

(require racket/base
         racket/match
         racket/list
         racket/string)

(provide check-nfr01-ast-equivalence
         check-nfr02-static-safety-matrix
         run-patterns-checker-v2
         all-v1-v2-macro-names
         macro->hc-fixture-id
         macro->kind)

(define all-v1-v2-macro-names
  '(defreflect-agent
    defrouter-agent
    defchain-agent
    defparallel-agent
    defplanner-agent
    defpriority-agent
    defdecomposition-agent
    deffsm-agent
    defevaluator-agent
    deftopic-model-agent
    defdecomposer-agent
    defguardrails-safety-agent
    defhitl-agent
    defexception-agent
    defexploration-agent))

(define (macro->kind m)
  (cond
    ((memq m '(defreflect-agent defrouter-agent defchain-agent defparallel-agent defplanner-agent)) 'v1)
    (else 'v2)))

(define (macro->hc-fixture-id m)
  (case m
    ((defreflect-agent)   'code-refiner)
    ((defrouter-agent)    'ops-gateway)
    ((defchain-agent)     'doc-pipeline)
    ((defparallel-agent)  'multi-search)
    ((defplanner-agent)   'deep-researcher)
    ((defpriority-agent)             'priority01_hc)
    ((defdecomposition-agent)        'decomp02_hc)
    ((deffsm-agent)                  'fsm03_hc)
    ((defevaluator-agent)            'eval04_hc)
    ((deftopic-model-agent)          'topic05_hc)
    ((defdecomposer-agent)           'decom06_hc)
    ((defguardrails-safety-agent)    'guard07_hc)
    ((defhitl-agent)                 'hitl08_hc)
    ((defexception-agent)            'exc09_hc)
    ((defexploration-agent)          'explore10_hc)
    (else #f)))

(define (v1-define-agent? form)
  (and (pair? form) (memq (car form) '(define-agent defagent))))

(define (ok? v) (and v #t))

;; 注意：本 codebase 的 Core AST 里 :model / :harness 等是 **symbol**（Racket 的
;; #:keyword 才是 keyword；":model" 只是冒号开头的 symbol）。CR-42 F2 修：统一返回
;; symbol 口径（原实现返回 keyword，导致 bucket->idx 永远 999、三必块永远缺失、
;; harness c/v/c 永远走 "无 harness" 分支假通过）。
(define (block-tag b)
  (cond
    ((and (pair? b) (keyword? (car b))) (string->symbol (keyword->string (car b))))
    ((and (pair? b) (symbol? (car b))) (car b))
    (else #f)))

(define *5-bucket-order* '(:model :tools :context :harness :multiagent))

(define (bucket->idx b)
  (let ((tag (block-tag b)))
    (or (for/or ((o (in-list *5-bucket-order*)) (i (in-naturals)))
          (and (eq? o tag) i))
        999)))

(define (check-prefix-sorted-5-bucket blocks)
  (let loop ((xs blocks) (prev-idx -1))
    (cond
      ((null? xs) #t)
      (else
       (let ((idx (bucket->idx (car xs))))
         (and (>= idx prev-idx)
              (< idx 5)
              (loop (cdr xs) idx)))))))

(define (three-mandatory-blocks-present? blocks)
  (let ((tags (map block-tag blocks)))
    (and (memq ':model tags) (memq ':tools tags) (memq ':context tags) #t)))


(define (harness-cvc-trichotomy blocks)
  (let ((harness-block (for/or ((b blocks))
                         (and (eq? (block-tag b) ':harness) b))))
    (if (not harness-block)
        #t
        (let ((tags (let loop ((xs (cdr harness-block)) (acc '()))
                      (cond
                        ((null? xs) (reverse acc))
                        ((and (pair? xs) (pair? (car xs)))
                         (let ((sub (car xs)))
                           (cond
                             ((and (pair? sub) (symbol? (car sub)))
                              (loop (cdr xs) (cons (car sub) acc)))
                             (else (loop (cdr xs) acc)))))
                        (else (loop (cdr xs) acc))))))
          (and (memq ':constrain tags) (memq ':verify tags) (memq ':correct tags) #t)))))

(define (no-runtime-eval-subst? datum)
  (cond
    ((pair? datum) (and (no-runtime-eval-subst? (car datum))
                        (no-runtime-eval-subst? (cdr datum))))
    ((symbol? datum) (not (memq datum '(eval apply eval-syntax syntax-local-value))))
    (else #t)))

(define (kw-args-sexpr-equal? a b head-len)
  (let ((a* (drop a head-len)) (b* (drop b head-len)))
    (equal? a* b*)))

(define-syntax-rule (report! result-list ok? id category description . extra)
  (set! result-list (cons (list id category ok? description . extra) result-list)))

(define (check-nfr01-ast-equivalence get-hc-expanded-fn get-hc-handwritten-fn)
  (let ((results '()))
    (for ((m (in-list all-v1-v2-macro-names)))
      (let* ((hc-id (macro->hc-fixture-id m))
             (expanded (and hc-id (get-hc-expanded-fn m hc-id)))
             (handwritten (and hc-id (get-hc-handwritten-fn m hc-id))))
        (cond
          ((or (not expanded) (not handwritten))
           (set! results (cons (list (symbol->string m) 'NFR01-HC #f "HC fixture missing" expanded handwritten) results)))
          ((not (v1-define-agent? expanded))
           (set! results (cons (list (symbol->string m) 'NFR01-HC #f "expanded not define-agent shape" (take expanded (min 3 (length expanded)))) results)))
          ((not (v1-define-agent? handwritten))
           (set! results (cons (list (symbol->string m) 'NFR01-HC #f "handwritten not define-agent shape" (take handwritten (min 3 (length handwritten)))) results)))
          ((not (equal? (cadr expanded) (cadr handwritten)))
           (set! results (cons (list (symbol->string m) 'NFR01-HC #f "agent name mismatch" (cadr expanded) (cadr handwritten)) results)))
          ((not (kw-args-sexpr-equal? expanded handwritten 2))
           (set! results (cons (list (symbol->string m) 'NFR01-HC #f "HC 5-bucket AST not byte-equal (sexpr-level)" ) results)))
          (else
           (set! results (cons (list (symbol->string m) 'NFR01-HC #t "HC expanded === handwritten AST byte-equal") results))))))
    (reverse results)))

;; CR-42 F3：NFR02 口径统一为 8 维 × 15 宏 = 120 checkpoint，与 Python 侧
;; tests/patterns/test_pattern_checker_v2.py 的 EIGHT_CELL_KEYS/EIGHT_CELL_LABELS 严格同集。
;; 删除原 d2-1（:pattern-kind tag）/ d2-2（:pattern-config kv）两维：这两个键不在
;; Core AST 白名单（compiler/agentlisp_compiler.rkt keyword-kvs 硬校验），产物含之即无法编译。
(define *nfr02-cell-specs*
  ;; (cell-key label value-thunk)；thunk 在拿到 blocks/expanded 后求值。
  (list (cons "d1-1" "5-bucket升序")
        (cons "d1-2" "三必块model/tools/context")
        (cons "d3-1" "harness c/v/c trichotomy")
        (cons "d3-2" "无运行时eval污染")
        (cons "d4-1" "agent name是symbol")
        (cons "d4-2" "block count 3≤n≤5")
        (cons "d5-1" "顶层形状define-agent")
        (cons "d5-2" "每block是list带kw tag")))

(define (check-nfr02-static-safety-matrix get-expanded-fn)
  (let ((results '()))
    (for ((m (in-list all-v1-v2-macro-names)))
      (let* ((hc-id (macro->hc-fixture-id m))
             (expanded (and hc-id (get-expanded-fn m hc-id)))
             (blocks (and expanded (pair? expanded) (> (length expanded) 2) (cddr expanded))))
        (when (and expanded blocks)
          (let ((cell-ok (hash 'd1-1 (check-prefix-sorted-5-bucket blocks)
                               'd1-2 (three-mandatory-blocks-present? blocks)
                               'd3-1 (harness-cvc-trichotomy blocks)
                               'd3-2 (no-runtime-eval-subst? expanded)
                               'd4-1 (symbol? (cadr expanded))
                               'd4-2 (and (number? (length blocks))
                                          (>= (length blocks) 3)
                                          (<= (length blocks) 5)
                                          #t)
                               'd5-1 (v1-define-agent? expanded)
                               'd5-2 (andmap (lambda (b) (and (list? b) (symbol? (block-tag b)))) blocks))))
            (for ((spec (in-list *nfr02-cell-specs*)))
              (set! results
                    (cons (list (format "~a|~a" (symbol->string m) (car spec))
                                'NFR02-MATRIX
                                (hash-ref cell-ok (string->symbol (car spec)))
                                (cdr spec))
                          results)))))))
    (reverse results)))

(define (run-patterns-checker-v2 get-hc-expanded-fn get-hc-handwritten-fn get-gen-expanded-fn)
  (let* ((nfr01-hc (check-nfr01-ast-equivalence get-hc-expanded-fn get-hc-handwritten-fn))
         (nfr01-gen (for/list ((m (in-list all-v1-v2-macro-names)))
                      (let* ((gen-datum (get-gen-expanded-fn m)))
                        (cond
                          ((or (not gen-datum) (not (pair? gen-datum)) (not (memq (car gen-datum) '(define-agent defagent))))
                           (list (symbol->string m) 'NFR01-GEN #f "GENERIC not define-agent shape" (and gen-datum (pair? gen-datum) (take gen-datum (min 3 (length gen-datum))))))
                          (else
                           (let ((blocks (cddr gen-datum)))
                             (if (check-prefix-sorted-5-bucket blocks)
                                 (list (symbol->string m) 'NFR01-GEN #t "GENERIC 5-bucket shape OK")
                                 (list (symbol->string m) 'NFR01-GEN #f "GENERIC 5-bucket 升序assert失败"))))))))
         (nfr02 (check-nfr02-static-safety-matrix get-hc-expanded-fn))
         (all (append nfr01-hc nfr01-gen nfr02)))
    (let ((pass (for/sum ((r all) #:when (caddr r)) 1))
          (fail (for/sum ((r all) #:unless (caddr r)) 1)))
      (values all pass fail))))
