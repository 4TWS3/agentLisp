#lang racket/base

;; =====================================================================
;; AgentLisp Checker (v2.0, spec/SRS 对齐版)
;; 模块职责：纯函数 AST 静态检查，不做 IO / 不做代码生成
;; 严格实现 SRS §4 三大 Compiler Invariants：
;;   1. ERR_KV_ALIGNMENT_VIOLATION     —— 静态段（:model/:tools）必须在动态段（:context）之前
;;   2. ERR_UNGUARDED_TOOL_EXECUTION  —— 有副作用 builtin 必须有 constrain / verify 护栏
;;   3. ERR_CONTEXT_LEAKAGE           —— scoped-worker define-tools 与父级重名 = 词法泄漏
;; 附加：shape 断言（CORRECT on_failure 枚举 / topology / layer / provider 值域）
;; =====================================================================

(provide check-agent
         check-kv-alignment-order
         check-unguarded-tool-execution
         check-context-leakage
         check-shapes

         ;; 枚举常量与工具函数，供 parser / tests / emitter 复用，
         ;; 保证全编译器唯一真值源（Single Source of Truth）
         CORRECT-ON-FAILURE-ENUM
         TOPOLOGY-ENUM
         MEMORY-LAYER-ENUM
         PROVIDER-ENUM
         SIDEEFFECT-BUILTIN-TOOLS

         ;; 异常：checker 抛的是 exn:agentlisp:check，message 以 [ERR_XXX] 开头
         exn:agentlisp:check?
         raise-check

         ;; 通用辅助
         to-str
         enum-member?)

(require racket/string
         racket/list
         racket/match)

;; ---------------------------------------------------------------------
;; 通用辅助（与 agentlisp_compiler.rkt 同名函数保持完全一致的实现，
;; 将来如果 agentlisp_compiler 改成 (require "checker.rkt")，可以直接删除
;; 主文件里的重复定义，避免双份维护）
;; ---------------------------------------------------------------------

(define (to-str v)
  (cond
    [(symbol? v) (symbol->string v)]
    [(string? v) v]
    [(number? v) (number->string v)]
    [(boolean? v) (if v "True" "False")]
    [else (format "~a" v)]))

(define (symbol<?/string a b)
  (string<? (to-str a) (to-str b)))

;; §3.4 枚举值域（Single Source of Truth，parser 也应该引用这里而不是自写常量）
(define CORRECT-ON-FAILURE-ENUM '(ask-human fallback-model abort))
(define TOPOLOGY-ENUM          '(peer orchestration decentralised judge-driven))
(define MEMORY-LAYER-ENUM      '(L0-Abstract L1-Overview L2-FullText))
(define PROVIDER-ENUM          '("anthropic" "openai" "qwen" "mock"))
(define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push))

(define (enum-member? v lst [->id to-str])
  (for/or ([x (in-list lst)]) (string=? (->id v) (->id x))))

;; ------------------------------ 异常 --------------------------------
(struct exn:agentlisp:check exn:fail () #:transparent)

(define (raise-check code msg)
  (raise (exn:agentlisp:check (format "[~a] ~a" code msg)
                              (current-continuation-marks))))

;; =====================================================================
;; 主入口 (check-agent parsed)
;; 失败条件：任一项检查抛出 exn:agentlisp:check
;; 成功条件：所有检查通过，返回原 parsed（可链式传给 emitter）
;; =====================================================================

(define (check-agent parsed)
  (check-kv-alignment-order   parsed)   ; SRS §4 Invariant #1
  (check-unguarded-tool-execution parsed)   ; SRS §4 Invariant #2
  (check-context-leakage      parsed)   ; SRS §4 Invariant #3
  (check-shapes               parsed)   ; 枚举值域形状 (AC-1 parser boundary 断言)
  parsed)

;; =====================================================================
;; Invariant #1：ERR_KV_ALIGNMENT_VIOLATION
;; 静态块（:model / :tools）必须严格出现在动态块（:context）之前
;; 注意：scoped-worker 内部也递归执行同样的顺序检查（P1 精细化，原实现仅外层）
;; =====================================================================

(define (check-kv-alignment-order parsed)
  (define order (hash-ref parsed 'order
                          (let-values ([(m c t h mu ord) (partition-blocks-guess
                                                          (hash-ref parsed 'raw '(defagent))
                                                          (hash-ref parsed 'name 'anon))])
                            ord)))
  (define ctx-pos   (index-of order ':context))
  (define model-pos (index-of order ':model))
  (define tools-pos (index-of order ':tools))
  (when (or (and model-pos ctx-pos (> model-pos ctx-pos))
            (and tools-pos ctx-pos (> tools-pos ctx-pos)))
    (raise-check 'ERR_KV_ALIGNMENT_VIOLATION
                 (format "静态块 (:model/:tools) 出现在动态块 :context 之后（实际顺序=~a）" order)))
  ;; P1 新增：递归检查 scoped-worker
  (define multi (hash-ref parsed 'multi #f))
  (when multi
    (for ([w (in-list (hash-ref multi 'workers '()))])
      (define w-order (hash-ref w 'order
                                (let-values ([(m c t h mu ord)
                                              (partition-blocks-guess
                                               `(scoped-worker ,(hash-ref w 'name) ,@(hash-ref w 'raw-blocks '()))
                                               (hash-ref w 'name))])
                                  ord)))
      (define w-ctx   (index-of w-order ':context))
      (define w-model (index-of w-order ':model))
      (define w-tools (index-of w-order ':tools))
      (when (or (and w-model w-ctx (> w-model w-ctx))
                (and w-tools w-ctx (> w-tools w-ctx)))
        (raise-check 'ERR_KV_ALIGNMENT_VIOLATION
                     (format "scoped-worker=~a: 静态块出现在动态块之后（实际顺序=~a）"
                             (hash-ref w 'name) w-order))))))

;; 兼容 helper：当 parsed 未提供 'order 时，从 raw 保守重算
;; 与主 parser 的 partition-blocks 语义相同，这里只抽最小必要子集
(define (partition-blocks-guess raw agent-name)
  (define blocks (if (and (pair? raw) (memq (car raw) '(defagent scoped-worker)))
                     (cddr raw)
                     raw))
  (let loop ([bs blocks] [model #f] [ctx #f] [tools #f] [harness #f] [multi #f] [order '()])
    (if (null? bs)
        (values model ctx tools harness multi (reverse order))
        (let ([b (car bs)] [rest (cdr bs)])
          (define tag (and (pair? b) (car b)))
          (cond
            [(eq? tag ':model)
             (loop rest b ctx tools harness multi (cons ':model order))]
            [(eq? tag ':context)
             (loop rest model b tools harness multi (cons ':context order))]
            [(eq? tag ':tools)
             (loop rest model ctx b harness multi (cons ':tools order))]
            [(eq? tag ':harness)
             (loop rest model ctx tools b multi (cons ':harness order))]
            [(eq? tag ':multiagent)
             (loop rest model ctx tools harness b (cons ':multiagent order))]
            [else (loop rest model ctx tools harness multi order)])))))

;; =====================================================================
;; Invariant #2：ERR_UNGUARDED_TOOL_EXECUTION
;; 任何列入 SIDEEFFECT-BUILTIN-TOOLS 的副作用 builtin 声明，
;; 必须满足以下三项的 OR：
;;   A) constrain.require_human_approval 显式列出该工具名，**AND**
;;      constrain.forbidden_commands 至少 1 条非空（安全基线护栏）
;;   B) verify 至少 1 项断言开启（json_schema / linter_check / test_runner / reviewer_agent）
;;   C) 工具根本不在 SIDEEFFECT-BUILTIN-TOOLS 内（纯读操作不受限）
;; =====================================================================

(define (check-unguarded-tool-execution parsed)
  (define builtins (hash-ref (hash-ref parsed 'tools) 'builtins '()))
  (define sideeffect-names
    (for/list ([b (in-list builtins)] #:when (member b SIDEEFFECT-BUILTIN-TOOLS symbol<?/string))
      b))
  (when (pair? sideeffect-names)
    (define harness (hash-ref parsed 'harness))
    (define constrain (hash-ref harness 'constrain))
    (define verify    (hash-ref harness 'verify))
    (define approval  (hash-ref constrain 'require_human_approval '()))
    (define forbidden (hash-ref constrain 'forbidden_commands '()))
    (define has-forbidden-non-empty?
      (for/or ([f (in-list forbidden)]) (not (string=? (to-str f) ""))))
    (define has-verify-any?
      (or (hash-ref verify 'json_schema)
          (hash-ref verify 'linter_check)
          (hash-ref verify 'test_runner)
          (hash-ref verify 'reviewer_agent)))
    (define unguarded
      (for/list ([n (in-list sideeffect-names)]
                 #:unless (or has-verify-any?
                              (and (for/or ([a approval]) (string=? a (to-str n)))
                                   has-forbidden-non-empty?)))
        n))
    (when (pair? unguarded)
      (raise-check
       'ERR_UNGUARDED_TOOL_EXECUTION
       (format "有副作用工具=~a 未被护栏保护：要求满足 (require_approval 明确列出 AND forbidden 非空) OR verify 任一项断言开启；当前 approval=~a forbidden=~a verify=~a"
               unguarded approval forbidden
               (list (hash-ref verify 'json_schema)
                     (hash-ref verify 'linter_check)
                     (hash-ref verify 'test_runner)
                     (hash-ref verify 'reviewer_agent))))))

  ;; P1 新增：递归 scoped-worker 侧工具同样要受 ERR_UNGUARDED 检查（原实现仅父级）
  (define multi (hash-ref parsed 'multi #f))
  (when multi
    (for ([w (in-list (hash-ref multi 'workers '()))])
      (define w-builtins (hash-ref (hash-ref w 'tools #hash()) 'builtins '()))
      (define w-sideeffect (for/list ([b w-builtins] #:when (member b SIDEEFFECT-BUILTIN-TOOLS symbol<?/string)) b))
      (when (pair? w-sideeffect)
        (define w-constrain (hash-ref (hash-ref w 'harness #hash()) 'constrain #hash()))
        (define w-verify    (hash-ref (hash-ref w 'harness #hash()) 'verify #hash()))
        (define w-ap (hash-ref w-constrain 'require_human_approval '()))
        (define w-fb (hash-ref w-constrain 'forbidden_commands '()))
        (define w-ver? (or (hash-ref w-verify 'json_schema #f)
                           (hash-ref w-verify 'linter_check #f)
                           (hash-ref w-verify 'test_runner #f)
                           (hash-ref w-verify 'reviewer_agent #f)))
        (define w-unguarded
          (for/list ([n w-sideeffect]
                     #:unless (or w-ver?
                                  (and (for/or ([a w-ap]) (string=? a (to-str n)))
                                       (for/or ([f w-fb]) (not (string=? (to-str f) ""))))))
            n))
        (when (pair? w-unguarded)
          (raise-check 'ERR_UNGUARDED_TOOL_EXECUTION
                       (format "scoped-worker=~a 侧有副作用工具=~a 无护栏（approval=~a forbidden=~a）"
                               (hash-ref w 'name) w-unguarded w-ap w-fb)))))))

;; =====================================================================
;; Invariant #3：ERR_CONTEXT_LEAKAGE
;; scoped-worker 内部的 define-tools 名必须与：
;;   (a) 父级 define-tools 完全不重名
;;   (b) 兄弟 scoped-worker 之间 define-tools 完全不重名
;; 满足任一项重名 = ERR_CONTEXT_LEAKAGE（离开作用域后 trajectory 可能误复用）
;; =====================================================================

(define (check-context-leakage parsed)
  (define multi (hash-ref parsed 'multi #f))
  (unless multi (void))
  (when multi
    (define parent-names
      (for/hash ([t (in-list (hash-ref (hash-ref parsed 'tools) 'define_tools '()))])
        (values (hash-ref t 'name) `(parent ,(hash-ref t 'name)))))
    (define workers (hash-ref multi 'workers '()))
    (define all-worker-names
      (for*/hash ([w workers] [t (hash-ref (hash-ref w 'tools #hash()) 'define_tools '())])
        (values (hash-ref t 'name) `(worker ,(hash-ref w 'name) ,(hash-ref t 'name)))))
    ;; (a) 父子冲突
    (for* ([(n info) (in-hash all-worker-names)]
           #:when (hash-has-key? parent-names n))
      (raise-check 'ERR_CONTEXT_LEAKAGE
                   (format "scoped-worker=~a 的工具名 ~a 与父级 define-tools 重名；离开作用域后可能导致父级 trajectory 意外复用，违反词法隔离"
                           (cadr info) n)))
    ;; (b) 兄弟冲突
    (let ([seen #hash()])
      (for* ([w workers]
             [t (hash-ref (hash-ref w 'tools #hash()) 'define_tools '())])
        (define n (hash-ref t 'name))
        (cond
          [(hash-has-key? seen n)
           (raise-check 'ERR_CONTEXT_LEAKAGE
                        (format "兄弟 scoped-worker 工具名冲突：worker=~a 与 worker=~a 均定义 ~a；可能导致 cross-worker trajectory 混淆"
                                (hash-ref seen n) (hash-ref w 'name) n))]
          [else (set! seen (hash-set seen n (hash-ref w 'name)))]))))))

;; =====================================================================
;; Shapes / 枚举值域断言（对齐 SRS §3 EBNF 枚举表）
;; 所有不通过以 ERR_CHECK_* 开头的错误码抛出，供 AC-1 parser boundary 反例断言
;; =====================================================================

(define (check-shapes parsed)
  ;; (1) harness.correct.on_failure ∈ CORRECT-ON-FAILURE-ENUM
  (define on-fail (hash-ref (hash-ref (hash-ref parsed 'harness) 'correct) 'on_failure))
  (unless (enum-member? on-fail CORRECT-ON-FAILURE-ENUM)
    (raise-check 'ERR_CHECK_HARNESS_CORRECT_ON_FAILURE_ENUM
                 (format "on_failure=~a，合法值=~a（注意：spec 使用连字符 ask-human，非下划线 ask_human）"
                         on-fail CORRECT-ON-FAILURE-ENUM)))

  ;; (2) model.provider ∈ PROVIDER-ENUM
  (define provider (hash-ref (hash-ref parsed 'model) 'provider))
  (unless (enum-member? provider PROVIDER-ENUM)
    (raise-check 'ERR_CHECK_MODEL_PROVIDER_ENUM
                 (format "model.provider=~a，合法值=~a" provider PROVIDER-ENUM)))

  ;; (3) model.temperature ∈ [0.0, 1.0]
  (define t (hash-ref (hash-ref parsed 'model) 'temperature))
  (unless (and (real? t) (>= t 0.0) (<= t 1.0))
    (raise-check 'ERR_CHECK_MODEL_TEMPERATURE_RANGE
                 (format "model.temperature=~a，要求 0.0 ≤ t ≤ 1.0（禁止 2.0 这类非法值）" t)))

  ;; (4) context.memory-policy.layers 子集 ⊆ MEMORY-LAYER-ENUM
  (define mp (hash-ref (hash-ref parsed 'context) 'memory_policy #f))
  (when mp
    (define layers (hash-ref mp 'layers '()))
    (for ([l (in-list layers)]
          #:unless (enum-member? l MEMORY-LAYER-ENUM))
      (raise-check 'ERR_CHECK_MEMORY_LAYER_ENUM
                   (format "memory-policy.layers 非法值 ~a，合法值=~a" l MEMORY-LAYER-ENUM))))

  ;; (5) multi.topology ∈ TOPOLOGY-ENUM
  (define multi (hash-ref parsed 'multi #f))
  (when multi
    (define top (hash-ref multi 'topology))
    (unless (enum-member? top TOPOLOGY-ENUM)
      (raise-check 'ERR_CHECK_MULTIAGENT_TOPOLOGY_ENUM
                   (format "topology=~a，合法值=~a" top TOPOLOGY-ENUM))))

  ;; (6) status_bar.custom 覆盖保留 key 仅 WARN（不抛）
  (define custom (hash-ref (hash-ref (hash-ref parsed 'context) 'status_bar) 'custom (hash)))
  (for ([k (in-list '("step_count" "current_branch" "test_status" "time_tracker" "todo_list"))])
    (when (hash-has-key? custom k)
      (log-warning "[WARN] status_bar.custom 覆盖保留键 ~a（可能被默认值覆盖）" k)))
  parsed)
