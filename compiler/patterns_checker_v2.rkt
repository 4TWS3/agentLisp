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

(define (block-tag b)
  (cond
    ((and (pair? b) (keyword? (car b))) (car b))
    ((and (pair? b) (symbol? (car b))) (string->keyword (symbol->string (car b))))
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

(define (pattern-kind-tag-present? blocks)
  (let find ((bs blocks))
    (cond
      ((null? bs) #f)
      (else
       (let ((b (car bs)))
         (or (and (list? b) (memq ':pattern-kind b))
             (and (list? b) (ormap (lambda (sub) (and (list? sub) (memq ':pattern-kind sub))) b))
             (find (cdr bs))))))))

(define (pattern-config-kv-present? blocks)
  (let find ((bs blocks))
    (cond
      ((null? bs) #f)
      (else
       (let ((b (car bs)))
         (or (and (list? b) (memq ':pattern-config b))
             (and (list? b) (ormap (lambda (sub) (and (list? sub) (memq ':pattern-config sub))) b))
             (find (cdr bs))))))))

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
                             ((and (pair? sub) (keyword? (car sub)))
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
           (set! results (cons (list (symbol->string m) 'NFR01-HC #t "HC expanded === handwritten AST byte-equal") results)))))
    (reverse results))))

(define (check-nfr02-static-safety-matrix get-expanded-fn)
  (let ((results '()))
    (for ((m (in-list all-v1-v2-macro-names)))
      (let* ((hc-id (macro->hc-fixture-id m))
             (expanded (and hc-id (get-expanded-fn m hc-id)))
             (blocks (and expanded (pair? expanded) (> (length expanded) 2) (cddr expanded))))
        (when (and expanded blocks)
          (let ((cp1 (check-prefix-sorted-5-bucket blocks))
                (cp2 (three-mandatory-blocks-present? blocks))
                (cp3 (pattern-kind-tag-present? blocks))
                (cp4 (pattern-config-kv-present? blocks))
                (cp5 (harness-cvc-trichotomy blocks))
                (cs1 (no-runtime-eval-subst? expanded))
                (cs2 (and (number? (length blocks))
                          (>= (length blocks) 3)
                          (<= (length blocks) 5)
                          #t))
                (cs3 (v1-define-agent? expanded))
                (cs4 (symbol? (cadr expanded)))
                (cs5 (andmap (lambda (b) (and (list? b) (keyword? (block-tag b)))) blocks)))
            (for ((idx (in-range 1 6)))
              (for ((jdx (in-range 1 3)))
                (let* ((cell-id (format "~a|~ax~a" (symbol->string m) idx jdx))
                       (label (cond
                                ((and (= idx 1) (= jdx 1)) "5-bucket升序")
                                ((and (= idx 1) (= jdx 2)) "三必块model/tools/context")
                                ((and (= idx 2) (= jdx 1)) "pattern-kind tag存在")
                                ((and (= idx 2) (= jdx 2)) "pattern-config kv存在")
                                ((and (= idx 3) (= jdx 1)) "harness c/v/c trichotomy")
                                ((and (= idx 3) (= jdx 2)) "无运行时eval污染")
                                ((and (= idx 4) (= jdx 1)) "agent name是symbol")
                                ((and (= idx 4) (= jdx 2)) "block count 3≤n≤5")
                                ((and (= idx 5) (= jdx 1)) "顶层形状define-agent")
                                ((and (= idx 5) (= jdx 2)) "每block是list带kw tag")
                                (else "unknown")))
                       (cell-ok (cond
                                 ((and (= idx 1) (= jdx 1)) cp1)
                                 ((and (= idx 1) (= jdx 2)) cp2)
                                 ((and (= idx 2) (= jdx 1)) cp3)
                                 ((and (= idx 2) (= jdx 2)) cp4)
                                 ((and (= idx 3) (= jdx 1)) cp5)
                                 ((and (= idx 3) (= jdx 2)) cs1)
                                 ((and (= idx 4) (= jdx 1)) cs4)
                                 ((and (= idx 4) (= jdx 2)) cs2)
                                 ((and (= idx 5) (= jdx 1)) cs3)
                                 ((and (= idx 5) (= jdx 2)) cs5)
                                 (else #f))))
                  (set! results (cons (list cell-id 'NFR02-MATRIX cell-ok label) results)))))))
    (reverse results)))))

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
