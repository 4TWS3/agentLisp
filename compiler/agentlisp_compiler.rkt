#lang racket

;; =====================================================================
;; AgentLisp 编译器 (spec v2.0 对齐版)
;; 对应原理：Agent = Model + Harness
;; 三段式架构：Parser(结构化解析+兜底) -> Checker(§4 三条ERR_ 不可变 + shape断言) -> Emitter(BaseHarnessV2 子类)
;; 修复 Code Review 14 项问题（详见仓库对话历史 review 清单）
;; =====================================================================

(require racket/string
         racket/function
         racket/match
         racket/file
         json
         ;; 关注点分离：parser/checker/emitter 三段式，checker 独立模块，枚举常量 Single Source of Truth
         "checker.rkt"
         ;; CR-42：模式注册表（数据驱动；加模式只改注册表，不改本文件分支）
         "pattern_registry.rkt"
         ;; drift 指纹：sha256（Racket 标准库无 sha256，见该文件顶部说明与自测）
         "sha256.rkt")

;; =====================================================================
;; 产物漂移（drift）指纹 —— Single Source of Truth
;; =====================================================================
;; 为什么需要：产物头部只写了一句 "DO NOT EDIT" 注释。注释是给人看的，
;;   机器不拦。重编译时手工改动被静默覆盖，无提示、无退出码。
;; 做法：产物内嵌**全文件**的 sha256（字段 `_AGENTLISP_CONTENT_SHA256`）。
;;   两个用途：
;;     (a) 机器拦：重编译前把「磁盘文件」与「本次将要写入的文本」都做规范化
;;         （指纹字段置空）后逐字节比对；不一致 = 上次生成后有人手工改过
;;         → 拒绝覆盖（除非 --force）。
;;     (b) 可审计：读产物即可核对该文件是否仍是编译器写的那一份。
;; 为什么比对「规范化全文」而不是「头部那个指纹字符串」：
;;   只比指纹字符串时，**尾部追加的内容不进入比较** —— 实测（2026-10-14）
;;   往产物末尾追加一行，只读校验照样报 CLEAN（假绿）。
;;   指纹必须覆盖它声称覆盖的全部内容，否则它是装饰品，不是闸门。
;; 为什么指纹 = 「全文件」而不是「本次生成段」：
;;   落盘文件 = 生成段 + 尾注（emit-harness-registry 里的 __main__ 块）。
;;   只签生成段就会漏掉尾注。故整段拼装后统一签名，再嵌回每个 agent 块的头。
(define CONTENT-SHA256-FIELD "_AGENTLISP_CONTENT_SHA256")
;; 必须用 pregexp（Perl 方言）而非 regexp（POSIX 方言）。
;; 教训（实测 2026-10-14）：POSIX `regexp` **不认 `{m,n}` 量词**，`(regexp "…{64}")`
;;   会静默构造出一个永不匹配的模式 —— 不报错、不抛异常，只是匹配失败。
;;   后果：sign-content / embedded-content-sha256 全线假绿，指纹永不落地。
;;   同一轮踩了两次（先是写死 {64} 匹配不上占位形态，再是 POSIX 方言）。
;; 宽口径（{0,64}）：同时匹配占位形态（空值）与已签名形态（64 位 hex）。
;; 为什么要匹配空值：指纹必须能对「指纹字段留空的文本」自洽计算，否则算不出来。
;; WS 里含真实 TAB：pregexp **不认** `\t` 转义（报 illegal alphabetic escape），
;; 也不认 POSIX 的 `[[:space:]]`。故用真实字符，不写作义序列。
(define WS "[ \t]")
(define CONTENT-SHA256-PATTERN
  (pregexp (format "~a~a*=~a*\"([0-9a-f]{0,64})\"" (regexp-quote CONTENT-SHA256-FIELD) WS WS)))
;; 严格口径：只认「已签名」形态。提取磁盘指纹时用，避免把空值当有效指纹。
(define CONTENT-SHA256-SIGNED-PATTERN
  (pregexp (format "~a~a*=~a*\"([0-9a-f]{64})\"" (regexp-quote CONTENT-SHA256-FIELD) WS WS)))

(provide compile-agent-lisp
         ;; 也开放给 CI / checker.rkt 复用：
         parse-defagent
         check-agent
         agent->py
         ;; drift 指纹（main.rkt / 独立校验脚本 / 测试共用同一口径，禁止各自实现）
         CONTENT-SHA256-FIELD
         CONTENT-SHA256-PATTERN
         CONTENT-SHA256-SIGNED-PATTERN
         build-generated-python
         signed-content-of
         agent->py-unsigned
         canonical-for-sha256
         digest-of-unsigned
         sign-content
         embedded-content-sha256
         file-content-drifted?
         ;; 枚举常量重导出（保持向后兼容：所有调用方 require 本文件时，行为不变）
         CORRECT-ON-FAILURE-ENUM
         TOPOLOGY-ENUM
         MEMORY-LAYER-ENUM
         PROVIDER-ENUM
         SIDEEFFECT-BUILTIN-TOOLS
         to-str
         enum-member?

         ;; JSON 结构化错误重导出（SRS §5.1 --json-errors）
         exn:agentlisp:check?
         exn:agentlisp:parse?
         exn:agentlisp:check->jsexpr
         exn->jsexpr
         checker-default-jsexpr-version
         checker-errors->jsexpr-list-thunk
         with-srcloc-from-form
         current-checker-source-name
         raise-check
         raise-parse-with-srcloc
         )

;; ---------------------------------------------------------------------
;; 通用辅助函数（以下函数仍保留在主文件，因为 emitter 段还要用）
;; 注意：to-str / enum-member? 已在 checker.rkt 提供，这里只是保留
;; 重导出用的临时包装，避免对其他调用方的破坏性重构。
;; ---------------------------------------------------------------------

;; (定义由 checker.rkt 提供)

;; PascalCase：修复 CRIT-12 class 连字符 SyntaxError
(define (pascal-case s)
  (define tokens (regexp-split #rx"[-_ ]+" (to-str s)))
  (apply string-append
         (for/list ([tok (in-list tokens)])
           (if (string=? tok "")
               ""
               (string-append (string-upcase (substring tok 0 1))
                              (substring tok 1 (string-length tok)))))))

;; 三引号字符串：修复 MINOR-11 长 system prompt 压成一行不可读
(define (py-string v)
  (define s (to-str v))
  (cond
    [(and (string-contains? s "\n") (not (string-contains? s "\"\"\"")))
     (string-append "\"\"\"" s "\"\"\"")]
    [else (format "~s" s)]))

(define (py-list/str xs)
  (string-append "[" (string-join (map py-string xs) ", ") "]"))

;; ------------------------------ 异常 --------------------------------
;; 注意：
;;   - checker 异常类型现在在 checker.rkt 提供（exn:agentlisp:check）
;;   - parser 异常类型也迁移到 checker.rkt（exn:agentlisp:parse），这样 --json-errors 时两者 shape 统一
;;   - 这里只保留 legacy 层：raise-parse → 统一转 raise-parse-with-srcloc（为了老调用方不 break）

(define (raise-parse where msg)
  (raise-parse-with-srcloc
   'PARSE_GENERIC
   (format "[PARSE_GENERIC] ~a: ~a" where msg)
   #:srcloc #f
   #:agent-name (cond
                  [(and (pair? where) (eq? (car where) 'defagent) (pair? (cdr where)))
                   (to-str (cadr where))]
                  [else #f])
   #:hints (list (format "原 raise-parse where=~a msg=~a" where msg)
                 "若要启用 --json-errors 的精准红波浪定位，请改调用 raise-parse-with-srcloc #:srcloc 参数")))

;; 辅助（保留在主文件，emitter 仍要用）
(define (->racket-bool v) (and v (not (eq? v #f))))

;; 宏展开（syntax->datum）可能把枚举值带成 (quote X)；统一脱壳，
;; 让裸符号与引用两种写法都能通过枚举校验（SRS 规范写法是裸符号）。
(define (unwrap-quote x)
  (if (and (pair? x) (eq? (car x) 'quote) (pair? (cdr x))) (cadr x) x))
(define (py-bool v) (if (->racket-bool v) "True" "False"))
(define (symbol<?/string a b) (string<? (to-str a) (to-str b)))

;; =====================================================================
;; 1. PARSER  修复 CRIT-1 / MAJOR-5 / MAJOR-7 / MAJOR-8 / MAJOR-9
;;   §3.4 枚举值域由 checker.rkt 常量 Single Source of Truth（parser 侧引用同一常量保证一致）
;; =====================================================================

;; defagent name Model Context Tools Harness [MultiAgent]
(define (parse-defagent form)
  (match form
    ;; 同时接受 defagent（spec 旧写法）与 define-agent（宏展开/夹具的规范产物）
    [(list (or 'defagent 'define-agent) name blocks ...)
     ;; partition-blocks 现在返回一个 hash（原先 7 个返回值，解构与重复调用都易错）
     (define pb (partition-blocks blocks name))
     (define model   (hash-ref pb 'model))
     (define ctx     (hash-ref pb 'context))
     (define tools   (hash-ref pb 'tools))
     (define harness (hash-ref pb 'harness))
     (define multi   (hash-ref pb 'multiagent))
     (define st      (hash-ref pb 'state))
     (define wf      (hash-ref pb 'workflow))
     (define parsed-state (and st (parse-state st)))
     (define state-fields
       (if parsed-state (map (lambda (f) (hash-ref f 'name)) (hash-ref parsed-state 'fields)) '()))
     (define state-defaulted
       (if parsed-state
           (for/hash ([f (in-list (hash-ref parsed-state 'fields))])
             (values (hash-ref f 'name) (hash-ref f 'has-default)))
           (hash)))
     ;; F-AMS-1：:workflow（单 agent 多步骤）与 :multiagent（多 agent）互斥。
     (when (and multi wf)
       (raise-parse `(defagent ,name)
                    ":workflow 与 :multiagent 互斥（F-AMS-1：单 agent 多步骤 vs 多 agent）"))
     (unless model   (raise-parse `(defagent ,name) "缺少必需的 :model 块"))
     (unless ctx     (raise-parse `(defagent ,name) "缺少必需的 :context 块"))
     (unless tools   (raise-parse `(defagent ,name) "缺少必需的 :tools 块"))
     (unless harness (raise-parse `(defagent ,name) "缺少必需的 :harness 块"))
     (define parsed-patterns
       ;; CR-42：查注册表校验 kind 与 config；非法即编译期报错（可静态断言）
       (for/list ([blk (in-list (hash-ref pb 'patterns))])
         (define-values (kind cfg errs) (validate-pattern-block blk))
         (when (pair? errs)
           (raise-parse ':pattern (string-join errs "；")))
         (hash 'kind kind 'config cfg)))
     ;; RSI 契约 §5.1：(:evolution …) 可选；缺省 #f
     (define evo (hash-ref pb 'evolution #f))
     (define parsed-evolution (and evo (parse-evolution evo)))
     (hash 'name name
           'patterns parsed-patterns
           'evolution parsed-evolution
           'model   (parse-model model)
           'context (parse-context ctx)
           'tools   (parse-tools tools)
           'harness (parse-harness harness)
           'multi   (and multi (parse-multi multi))
           'state   parsed-state
           'workflow (cond
                       [wf (parse-workflow wf state-fields state-defaulted
                                           (and (pair? (filter (lambda (p)
                                                                 (equal? (format "~a" (hash-ref p 'kind))
                                                                         "parallel"))
                                                               parsed-patterns))
                                                #t))]
                       ;; D2 内聚：:multiagent 降成 :workflow + subagent 节点
                       [multi (multi->workflow (parse-multi multi))]
                       [else #f])
           'order   (hash-ref pb 'order)
           'raw form)]
    [_ (raise-parse 'parse-defagent (format "顶层必须是 (defagent NAME BLOCK…)，得到：~s" form))]))

;;; ---------- RSI 演进契约 §5.1：(:evolution …) ----------
;; 值域封闭：突变目标与不可变不变量都只能取白名单内的符号。
;; 这样离线 Evolver 生成的 :evolution 若越界，会在编译期被拦下。
(define evolution-mutation-targets
  '(:pattern-macros :prompt-patches :skills :harness-retry))
(define evolution-invariants
  '(:kv-alignment :workspace-root :forbidden-commands :model-provider))

(define (parse-online-trace v)
  (cond [(eq? v #t) #t]
        [(eq? v #f) #f]
        [else (raise-parse ':evolution (format "(:online-trace …) 必须是 #t 或 #f，得到 ~s" v))]))

;; RSI 规格把目标/不变量写成 'skills（符号），实现写成 :skills（关键字）。两种都收。
(define (evolution-normalize-sym s)
  (cond [(not (symbol? s)) s]
        [(let ([str (symbol->string s)])
           (and (> (string-length str) 0) (char=? (string-ref str 0) #\:))) s]
        [else (string->symbol (string-append ":" (symbol->string s)))]))

(define (parse-target-list ts)
  (when (null? ts) (raise-parse ':evolution ":mutation-targets 不能为空"))
  (for/list ([t (in-list ts)])
    (define n (evolution-normalize-sym t))
    (unless (memq n evolution-mutation-targets)
      (raise-parse ':evolution
                   (format "未知突变目标 ~s；允许：~s" t evolution-mutation-targets)))
    n))

(define (parse-invariant-list is)
  (for/list ([i (in-list is)])
    (define n (evolution-normalize-sym i))
    (unless (memq n evolution-invariants)
      (raise-parse ':evolution
                   (format "未知不变量 ~s；允许：~s" i evolution-invariants)))
    n))

;; FR-EVO-2（US-47）：突变目标侵入不可变不变量 -> ERR_IMMUTABLE_INVARIANT_VIOLATION
;; 在枚举校验之前比原始符号，这样错误更具体（先报侵入，不报未知不变量）。
(define (check-invariant-overlap raw-targets raw-invariants)
  (define norms (map evolution-normalize-sym raw-invariants))
  (for ([t (in-list raw-targets)])
    (define n (evolution-normalize-sym t))
    (when (memq n norms)
      (raise-check 'ERR_IMMUTABLE_INVARIANT_VIOLATION
                   (format "突变目标 ~s 同时列为不可变不变量（FR-EVO-2）" t)))))

(define (keyword-evolution? blk)
  (and (pair? blk) (pair? (cdr blk)) (dsl-key? (cadr blk))))

(define (evolution-prop props tag)
  (let loop ([xs props])
    (cond [(null? xs) #f]
          [(and (list? (car xs)) (pair? (car xs)) (eq? (car (car xs)) tag)) (car xs)]
          [else (loop (cdr xs))])))

(define (parse-evolution blk)
  (cond
    ;; US-47：RSI 规格的 keyword 形式（§3.1 EBNF）
    [(keyword-evolution? blk)
     (define kw (keyword-kvs (cdr blk)
                             '(:online-trace :offline-evolver :mutation-targets
                               :immutable-invariants :verifier-gate)))
     (define raw-targets (hash-ref kw ':mutation-targets '()))
     (define raw-invariants (hash-ref kw ':immutable-invariants '()))
     (check-invariant-overlap raw-targets raw-invariants)
     (define targets (parse-target-list raw-targets))
     (define invariants (parse-invariant-list raw-invariants))
     (hash 'online-trace (if (hash-has-key? kw ':online-trace)
                             (parse-online-trace (hash-ref kw ':online-trace))
                             #f)
           'offline-evolver (if (hash-has-key? kw ':offline-evolver)
                                (to-str (hash-ref kw ':offline-evolver))
                                "")
           'mutation-targets targets
           'immutable-invariants invariants
           'verifier-gate (parse-verifier-gate (hash-ref kw ':verifier-gate #f)))]
    [else
     (define props (cdr blk))
     (define ot (evolution-prop props ':online-trace))
     (define oe (evolution-prop props ':offline-evolver))
     (define mt (evolution-prop props ':mutation-targets))
     (define iv (evolution-prop props ':immutable-invariants))
     (define vg (evolution-prop props ':verifier-gate))
     (unless (and mt iv vg)
       (raise-parse ':evolution
                    "必需是 (:evolution [(:online-trace #t|#f)] (:mutation-targets …) (:immutable-invariants …) (:verifier-gate …)) 或 keyword 形式"))
     (check-invariant-overlap (cdr mt) (cdr iv))
     (define targets (parse-target-list (cdr mt)))
     (define invariants (parse-invariant-list (cdr iv)))
     (hash 'online-trace (if ot (parse-online-trace (cadr ot)) #f)
           'offline-evolver (if oe (to-str (cadr oe)) "")
           'mutation-targets targets
           'immutable-invariants invariants
           'verifier-gate (parse-verifier-gate vg))]))

(define (parse-verifier-gate vg)
  ;; 两种写法：(:verifier-gate "名" :min-pass-rate N :mcnemar-p-threshold N)
  ;;           (:verifier-gate (:suite "名") :min-pass-rate N :mcnemar-p-threshold N)
  (define body
    (match vg
      [(list ':verifier-gate (list ':suite nm) k1 v1 k2 v2) (list nm k1 v1 k2 v2)]
      [(list ':verifier-gate nm k1 v1 k2 v2) (list nm k1 v1 k2 v2)]
      [(list ':suite nm k1 v1 k2 v2) (list nm k1 v1 k2 v2)]
      [_ (raise-parse ':evolution
                      ":verifier-gate 必需是 (:verifier-gate [( :suite ) \"名称\"] :min-pass-rate N :mcnemar-p-threshold N)")]))
  (match-define (list nm k1 v1 k2 v2) body)
  (unless (and (string? nm) (not (string=? nm "")))
    (raise-parse ':evolution ":verifier-gate 的名称必须是非空字符串"))
  (unless (eq? k1 ':min-pass-rate)
    (raise-parse ':evolution ":verifier-gate 缺 :min-pass-rate"))
  (unless (eq? k2 ':mcnemar-p-threshold)
    (raise-parse ':evolution ":verifier-gate 缺 :mcnemar-p-threshold"))
  (unless (real? v1) (raise-parse ':evolution ":min-pass-rate 必须是数"))
  (unless (real? v2) (raise-parse ':evolution ":mcnemar-p-threshold 必须是数"))
  (hash 'name nm
        'min-pass-rate (exact->inexact v1)
        'mcnemar-p-threshold (exact->inexact v2)))

;;; ---------- F-AMS-3（US-04）：(:state :fields …) ----------
;; 状态字段：具名 + 类型 + 可选默认值。类型枚举封闭（新增类型要改这里，测试会红）。
(define STATE-TYPE-ENUM '("dict" "str" "int" "float" "bool" "list"))

(define (parse-state form)
  (match form
    [`(:state . ,kvs)
     (let ([kw (keyword-kvs kvs '(:fields))])
       (unless (hash-has-key? kw ':fields)
         (raise-parse ':state "缺必需 :fields"))
       (define raw (hash-ref kw ':fields))
       (unless (and (list? raw) (pair? raw))
         (raise-parse ':state ":fields 必须是非空列表：((名 :type T [:default D]) …)"))
       (hash 'fields
             (for/list ([f (in-list raw)])
               (unless (and (list? f) (>= (length f) 3) (symbol? (car f)))
                 (raise-parse ':state (format "字段格式应为 (名 :type T [:default D])，得到 ~s" f)))
               (define nm (symbol->string (car f)))
               (define kw2 (keyword-kvs (cdr f) '(:type :default)))
               (unless (hash-has-key? kw2 ':type)
                 (raise-parse ':state (format "字段 ~a 缺 :type" nm)))
               (define ty (to-str (hash-ref kw2 ':type)))
               (unless (member ty STATE-TYPE-ENUM)
                 (raise-parse ':state
                              (format "字段 ~a 的 :type 枚举=~a，得到 ~a" nm STATE-TYPE-ENUM ty)))
               (hash 'name nm 'type ty
                     'has-default (hash-has-key? kw2 ':default)
                     'default (if (hash-has-key? kw2 ':default) (hash-ref kw2 ':default) #f)))))]
    [_ (raise-parse ':state "必需是 (:state :fields ((名 :type T [:default D]) …))")]))

;;; ---------- F-AMS-1 / F-AMS-2（US-05 / US-07 / US-09）：(:workflow …) ----------
(define WORKFLOW-NODE-TYPES '("agent" "computation" "evaluator" "subagent"))
(define WORKFLOW-TOPOLOGY-ENUM '("sequential" "edge" "conditional-edge" "conditional-loop"))

(define (valid-handler? s)
  (and (string? s)
       (regexp-match? #rx"^[A-Za-z_][A-Za-z0-9_]*([.][A-Za-z_][A-Za-z0-9_]*)+$" s)))

;; 节点/边的前向可达（conditional-loop 的环也算可达，但不算前向边）
(define (wf-step edge-pairs from)
  (for/list ([p (in-list edge-pairs)] #:when (string=? (car p) from)) (cdr p)))

(define (wf-reachable entry edge-pairs)
  (let loop ([frontier (list entry)] [seen '()])
    (cond [(null? frontier) seen]
          [(member (car frontier) seen) (loop (cdr frontier) seen)]
          [else (loop (append (cdr frontier) (wf-step edge-pairs (car frontier)))
                      (cons (car frontier) seen))])))

(define (wf-reach-problems entry nodes edge-pairs)
  (define seen (wf-reachable entry edge-pairs))
  (for/list ([n (in-list (map (lambda (x) (hash-ref x 'name)) nodes))]
             #:when (not (member n seen)))
    (format "工作流节点 ~a 从入口 ~a 不可达（F-AMS-1）" n entry)))

(define (wf-cycle-problems nodes edge-pairs)
  (define color (make-hash))
  (for ([n (in-list (map (lambda (x) (hash-ref x 'name)) nodes))]) (hash-set! color n 0))
  (define found '())
  (define (visit n)
    (hash-set! color n 1)
    (for ([m (in-list (wf-step edge-pairs n))])
      (define c (hash-ref color m 0))
      (cond [(= c 1)
             (set! found (cons (format "工作流存在未声明环：~a -> ~a（F-AMS-1；环必须用 conditional-loop）" n m)
                               found))]
            [(= c 0) (visit m)]
            [else (void)]))
    (hash-set! color n 2))
  (for ([n (in-list (map (lambda (x) (hash-ref x 'name)) nodes))])
    (when (= (hash-ref color n 0) 0) (visit n)))
  (reverse found))

(define WORKFLOW-EFFECT-ENUM '("pure" "revertible" "non_revertible"))

;; D2 内聚（US-06）：:multiagent 不再单独执行，降成 :workflow + subagent 节点。
;; 四种多 agent 拓扑映射到 workflow 的边表；隔离语义由节点 :isolation scoped 承载。
(define (multi->workflow multi)
  (define topo (hash-ref multi 'topology))
  (define workers (map (lambda (w) (hash-ref w 'name)) (hash-ref multi 'workers)))
  (define (edge a b) (hash 'from a 'to b 'kind "fanout"))
  (define nodes
    (for/list ([w (in-list workers)])
      (hash 'name w 'type "subagent" 'handler #f 'outputs '() 'static "" 'dynamic ""
            'reads '() 'effect "revertible" 'isolation "scoped")))
  ;; 全部线性化为 DAG：F-AMS-1 禁止未声明环，而多 agent 的 mesh/ring 天然有环。
  ;; 这是本轮的口径简化（已写进交底）：orchestration = hub 扇出；其余 = 链。
  (define edges
    (cond
      [(null? workers) '()]
      [(string=? topo "orchestration")
       (for/list ([w (in-list (cdr workers))]) (edge (car workers) w))]
      [else
       (for/list ([a (in-list workers)] [b (in-list (cdr workers))]) (edge a b))]))
  (hash 'entry (if (pair? workers) (car workers) "")
        'nodes nodes 'edges edges 'loops '()))

(define (parse-workflow form state-fields state-defaulted has-parallel)
  (match form
    [`(:workflow . ,kvs)
     (define kw (keyword-kvs kvs '(:entry :nodes :topology)))
     (unless (hash-has-key? kw ':entry) (raise-parse ':workflow "缺必需 :entry"))
     (unless (hash-has-key? kw ':nodes) (raise-parse ':workflow "缺必需 :nodes"))
     (define entry (to-str (hash-ref kw ':entry)))
     (define raw-nodes (hash-ref kw ':nodes))
     (unless (and (list? raw-nodes) (pair? raw-nodes))
       (raise-parse ':workflow ":nodes 必须是非空列表：((名 :type T [:handler \"m.f\"]) …)"))
     (define nodes
       (for/list ([n (in-list raw-nodes)])
         (unless (and (list? n) (pair? n) (symbol? (car n)))
           (raise-parse ':workflow (format "节点格式应为 (名 :type T …)，得到 ~s" n)))
         (define nm (symbol->string (car n)))
         (define kw2 (keyword-kvs (cdr n) '(:type :handler :prompt :output-fields :effect :isolation)))
         (unless (hash-has-key? kw2 ':type)
           (raise-parse ':workflow (format "节点 ~a 缺 :type" nm)))
         (define ty (to-str (hash-ref kw2 ':type)))
         (unless (member ty WORKFLOW-NODE-TYPES)
           (raise-parse ':workflow
                        (format "节点 ~a 的 :type 枚举=~a，得到 ~a" nm WORKFLOW-NODE-TYPES ty)))
         (define h (and (hash-has-key? kw2 ':handler) (to-str (hash-ref kw2 ':handler))))
         (when (and h (not (valid-handler? h)))
           (raise-parse ':workflow
                        (format "节点 ~a 的 :handler 格式应为 模块.函数 或 模块.类.方法，得到 ~s" nm h)))
         (when (and (string=? ty "computation") (not h))
           (raise-parse ':workflow (format "computation 节点 ~a 必须给 :handler（F-AMS-2）" nm)))
         ;; F-AMS-3：:output-fields 必须来自 :state 已声明字段
         (define outs (map to-str (hash-ref kw2 ':output-fields '())))
         (for ([o (in-list outs)])
           (unless (member o state-fields)
             (raise-parse ':workflow
                          (format "节点 ~a 的 :output-fields 含未声明字段 ~a（F-AMS-3）" nm o))))
         ;; F-AMS-5：:prompt 拆 :static / :dynamic。插值只准进 :dynamic。
         (define pr (and (hash-has-key? kw2 ':prompt) (hash-ref kw2 ':prompt)))
         (define pkw (and pr (keyword-kvs pr '(:static :dynamic))))
         (define stat (if pkw (to-str (hash-ref pkw ':static "")) ""))
         (define dyn (if pkw (to-str (hash-ref pkw ':dynamic "")) ""))
         (when (regexp-match? #rx"[{][A-Za-z_][A-Za-z0-9_]*[}]" stat)
           (raise-parse ':workflow
                        (format "节点 ~a 的 :static 段含插值（F-AMS-5 R1：插值只能进 :dynamic）" nm)))
         (define reads '())
         (for ([mm (in-list (regexp-match* #rx"[{][A-Za-z_][A-Za-z0-9_]*[}]" dyn))])
           (define f (substring mm 1 (sub1 (string-length mm))))
           (unless (member f state-fields)
             (raise-parse ':workflow
                          (format "节点 ~a 的 :dynamic 引用未声明字段 ~a（F-AMS-5 R3/R4）" nm f)))
           (set! reads (cons f reads)))
         ;; F-AMS-8（US-53）：效应等级。默认 pure。
         (define eff (to-str (hash-ref kw2 ':effect "pure")))
         (unless (member eff WORKFLOW-EFFECT-ENUM)
           (raise-parse ':workflow
                        (format "节点 ~a 的 :effect 枚举=~a，得到 ~a"
                                nm WORKFLOW-EFFECT-ENUM eff)))
         (define iso (to-str (hash-ref kw2 ':isolation "")))
         (unless (member iso '("" "scoped"))
           (raise-parse ':workflow
                        (format "节点 ~a 的 :isolation 只允许 scoped 或省略，得到 ~a" nm iso)))
         (hash 'name nm 'type ty 'handler h 'outputs outs
               'static stat 'dynamic dyn 'reads (reverse reads) 'effect eff
               'isolation iso)))
     ;; F-AMS-8：non_revertible 在并发（parallel）中必须串行 -> 编译期拦
     (when has-parallel
       (define nr (for/list ([n (in-list nodes)]
                             #:when (string=? (hash-ref n 'effect) "non_revertible"))
                    (hash-ref n 'name)))
       (when (pair? nr)
         (raise-parse ':workflow
                      (format "non_revertible 节点 ~a 不得与 :pattern parallel 并发（F-AMS-8：必须串行）"
                              nr))))
     ;; F-AMS-3（US-10）：字段可达性。只写不读 / 无人读写 -> 警告（不失败）。
     (define written (append* (map (lambda (n) (hash-ref n 'outputs)) nodes)))
     (define read-any (append* (map (lambda (n) (hash-ref n 'reads)) nodes)))
     (for ([f (in-list state-fields)])
       (define w? (and (member f written) #t))
       (define r? (and (member f read-any) #t))
       (cond
         ;; 用 eprintf 而非 log-warning：log-warning 默认不显示（需 PLTSTDERR），
         ;; 那等于静默。警告必须真能看到。
         [(not (or w? r?)) (eprintf "[WARN] 状态字段 ~a 无人读写（F-AMS-3）\n" f)]
         [(and w? (not r?)) (eprintf "[WARN] 状态字段 ~a 只写不读（F-AMS-3）\n" f)]
         [(and r? (not w?) (not (hash-ref state-defaulted f #f)))
          (raise-parse ':workflow
                       (format "状态字段 ~a 被读但无人写，且无 :default（F-AMS-3）" f))]))
     (define (node-exists? nm) (ormap (lambda (n) (string=? (hash-ref n 'name) nm)) nodes))
     (define raw-topo (hash-ref kw ':topology '()))
     (define edges '())
     (define loops '())
     (for ([t (in-list raw-topo)])
       (unless (and (list? t) (pair? t) (symbol? (car t)))
         (raise-parse ':workflow (format "拓扑格式应为 (类型 …)，得到 ~s" t)))
       (define ty (symbol->string (car t)))
       (unless (member ty WORKFLOW-TOPOLOGY-ENUM)
         (raise-parse ':workflow (format "拓扑类型枚举=~a，得到 ~a" WORKFLOW-TOPOLOGY-ENUM ty)))
       (cond
         [(string=? ty "sequential")
          (unless (and (= (length t) 2) (list? (cadr t)) (pair? (cadr t)))
            (raise-parse ':workflow "(sequential (n1 n2 …)) 需非空节点列表"))
          (define ns (map to-str (cadr t)))
          (for ([n (in-list ns)])
            (unless (node-exists? n)
              (raise-parse ':workflow (format "sequential 引用不存在的节点 ~a" n))))
          (for ([p (in-list (for/list ([a ns] [b (cdr ns)]) (list a b)))])
            (set! edges (cons (hash 'from (car p) 'to (cadr p) 'kind "sequential") edges)))]
         [(string=? ty "edge")
          (unless (= (length t) 3) (raise-parse ':workflow "(edge from to)"))
          (define a (to-str (cadr t)))
          (define b (to-str (caddr t)))
          (unless (node-exists? a) (raise-parse ':workflow (format "edge 引用不存在的节点 ~a" a)))
          (unless (node-exists? b) (raise-parse ':workflow (format "edge 引用不存在的节点 ~a" b)))
          (set! edges (cons (hash 'from a 'to b 'kind "edge") edges))]
         [(string=? ty "conditional-edge")
          (define kw3 (keyword-kvs (cdr t) '(:from :to :when)))
          (unless (and (hash-has-key? kw3 ':from) (hash-has-key? kw3 ':to))
            (raise-parse ':workflow "(conditional-edge :from a :to b [:when \"expr\"])"))
          (define a (to-str (hash-ref kw3 ':from)))
          (define b (to-str (hash-ref kw3 ':to)))
          (unless (node-exists? a)
            (raise-parse ':workflow (format "conditional-edge 引用不存在的节点 ~a" a)))
          (unless (node-exists? b)
            (raise-parse ':workflow (format "conditional-edge 引用不存在的节点 ~a" b)))
          (set! edges (cons (hash 'from a 'to b 'kind "conditional-edge") edges))]
         [else
          (define kw3 (keyword-kvs (cdr t) '(:nodes :while :max-rounds)))
          (unless (hash-has-key? kw3 ':nodes) (raise-parse ':workflow "conditional-loop 缺 :nodes"))
          (unless (hash-has-key? kw3 ':while) (raise-parse ':workflow "conditional-loop 缺 :while"))
          (define ns (map to-str (hash-ref kw3 ':nodes)))
          (unless (pair? ns) (raise-parse ':workflow "conditional-loop :nodes 需非空"))
          (for ([n (in-list ns)])
            (unless (node-exists? n)
              (raise-parse ':workflow (format "conditional-loop 引用不存在的节点 ~a" n))))
          (set! loops (cons (hash 'nodes ns
                                  'while (to-str (hash-ref kw3 ':while))
                                  'max-rounds (hash-ref kw3 ':max-rounds 0))
                            loops))]))
     (unless (node-exists? entry)
       (raise-parse ':workflow (format ":entry ~a 不是已声明节点" entry)))
     ;; 边表：前向边 + 环内边（用于可达性）
     (define forward (map (lambda (e) (cons (hash-ref e 'from) (hash-ref e 'to))) edges))
     (define loop-pairs
       (append*
        (for/list ([l (in-list loops)])
          (define ns (hash-ref l 'nodes))
          (append (for/list ([a ns] [b (cdr ns)]) (cons a b))
                  (list (cons (last ns) (first ns)))))))
     (define all-pairs (append forward loop-pairs))
     (define structure-problems
       (append (wf-reach-problems entry nodes all-pairs) (wf-cycle-problems nodes forward)))
     (when (pair? structure-problems)
       (raise-parse ':workflow (string-join structure-problems "；")))
     (hash 'entry entry 'nodes nodes 'edges (reverse edges) 'loops (reverse loops))]
    [_ (raise-parse ':workflow "必需是 (:workflow :entry N :nodes (…) [:topology (…)])")]))

(define (partition-blocks blocks agent-name)
  ;; CR-42：:pattern 可多次；:evolution 至多一次。US-04：:state 至多一次。
  ;; US-05：:workflow 至多一次（与 :multiagent 互斥，在 parse-defagent 里拦）。
  ;; 返回 hash，键：model context tools harness multiagent state workflow patterns evolution order
  (let loop ([bs blocks] [model #f] [ctx #f] [tools #f] [harness #f] [multi #f] [st #f] [wf #f]
             [pats '()] [evo #f] [order '()])
    (if (null? bs)
        (hash 'model model 'context ctx 'tools tools 'harness harness
              'multiagent multi 'state st 'workflow wf 'patterns (reverse pats)
              'evolution evo 'order (reverse order))
        (let ([b (car bs)] [rest (cdr bs)])
          (define tag (and (pair? b) (car b)))
          (cond
            [(eq? tag ':model)   (when model (raise-parse `(defagent ,agent-name) ":model 块重复"))
                                 (loop rest b ctx tools harness multi st wf pats evo (cons ':model order))]
            [(eq? tag ':context) (when ctx (raise-parse `(defagent ,agent-name) ":context 块重复"))
                                 (loop rest model b tools harness multi st wf pats evo (cons ':context order))]
            [(eq? tag ':tools)   (when tools (raise-parse `(defagent ,agent-name) ":tools 块重复"))
                                 (loop rest model ctx b harness multi st wf pats evo (cons ':tools order))]
            [(eq? tag ':harness) (when harness (raise-parse `(defagent ,agent-name) ":harness 块重复"))
                                 (loop rest model ctx tools b multi st wf pats evo (cons ':harness order))]
            [(eq? tag ':multiagent) (when multi (raise-parse `(defagent ,agent-name) ":multiagent 块重复"))
                                     (loop rest model ctx tools harness b st wf pats evo (cons ':multiagent order))]
            [(eq? tag ':state)   (when st (raise-parse `(defagent ,agent-name) ":state 块重复"))
                                 (loop rest model ctx tools harness multi b wf pats evo (cons ':state order))]
            [(eq? tag ':workflow) (when wf (raise-parse `(defagent ,agent-name) ":workflow 块重复"))
                                  (loop rest model ctx tools harness multi st b pats evo (cons ':workflow order))]
            [(eq? tag ':pattern)
             ;; CR-42：模式块交给注册表校验（kind/config），可多次出现
             (loop rest model ctx tools harness multi st wf (cons b pats) evo (cons ':pattern order))]
            [(eq? tag ':evolution)
             ;; RSI 契约 §5.1：至多一次；不存在时为 #f
             (when evo (raise-parse `(defagent ,agent-name) ":evolution 块重复"))
             (loop rest model ctx tools harness multi st wf pats b (cons ':evolution order))]
            [else (raise-parse `(defagent ,agent-name)
                                (format "未知块 ~s；应为 :model/:context/:tools/:harness（可选 :state/:workflow/:multiagent/:pattern/:evolution）" tag))])))))

;;; ---------- parse-model (修复 MAJOR-3 temperature 范围 + PROVIDER-ENUM 值域) ----------
(define (parse-model form)
  (match form
    [`(:model . ,kvs)
     (let ([kw (keyword-kvs kvs '(:provider :name :temperature :system-prompt))])
       (unless (hash-has-key? kw ':provider)     (raise-parse ':model "缺必需 :provider"))
       (unless (hash-has-key? kw ':name)         (raise-parse ':model "缺必需 :name"))
       (unless (hash-has-key? kw ':system-prompt)(raise-parse ':model "缺必需 :system-prompt"))
       (let* ([provider (hash-ref kw ':provider)]
              [name (hash-ref kw ':name)]
              [temp (hash-ref kw ':temperature 0.2)]
              [sysp (hash-ref kw ':system-prompt)])
         (unless (enum-member? provider PROVIDER-ENUM (lambda (x) (to-str x)))
           (raise-parse ':model (format ":provider 枚举=~a，得到 ~a" PROVIDER-ENUM provider)))
         (unless (and (real? temp) (<= 0.0 temp 1.0))
           (raise-parse ':model (format ":temperature 必须是 [0.0,1.0] 数，得到 ~a" temp)))
         (when (or (not (string? sysp)) (string=? (string-trim sysp) ""))
           (raise-parse ':model ":system-prompt 必须是非空字符串"))
         (hash 'provider (to-str provider) 'name (to-str name)
               'temperature (exact->inexact temp)
               'system_prompt sysp)))]
    [_ (raise-parse ':model (format "必需是 (:model …)，得到 ~s" form))]))

;;; ---------- parse-context (修复 MAJOR-8 auto-append-episodic→auto-append + 数据丢失；StatusBarItem 四件套) ----------
(define (parse-context form)
  (match form
    [`(:context . ,kvs)
     (let ([kw (keyword-kvs kvs '(:memory-policy :skills :status-bar :compression))])
       (define mp (hash-ref kw ':memory-policy #f))
       (define skills (hash-ref kw ':skills '()))
       (define sb (hash-ref kw ':status-bar #f))
       (define comp (hash-ref kw ':compression #f))
       (hash 'memory_policy (and mp (parse-memory-policy mp))
             'skills (map to-str skills)
             'status_bar (parse-status-bar sb)
             'compression (and comp (to-str comp))))]
    [_ (raise-parse ':context (format "必需是 (:context …)，得到 ~s" form))]))

(define (parse-memory-policy mp)
  (match mp
    [(? (lambda (x) (and (list? x) (member ':auto-append-episodic x))) _)
     (raise-parse-with-srcloc
      'FR-PARSER-3
      "[FR-PARSER-3] 使用了已废弃命名 :auto-append-episodic，请统一改为 spec 标准 :auto-append"
      #:srcloc #f
      #:agent-name #f
      #:hints (list "spec 层命名规范：用 :auto-append 禁用旧 :auto-append-episodic"
                    "emit 到 Python 运行时键名：context_config.auto_append_episodic（下划线，禁止连字符）"))]
    [`(:markdown-fs ,path :layers ,layers :auto-append ,append?)
     (unless (string? path) (raise-parse ':memory-policy "markdown-fs path 必须是字符串"))
     (define layer-syms (map unwrap-quote layers))
     (for ([l (in-list layer-syms)])
       (unless (enum-member? l MEMORY-LAYER-ENUM)
         (raise-parse ':memory-policy (format "layer 枚举=~a，得到 ~a" MEMORY-LAYER-ENUM l))))
     (hash 'path path 'layers (map to-str layer-syms)
           'auto_append_episodic (->racket-bool append?)  ; Python key：下划线
           'auto_append_spec_key ':auto-append)]           ; 原始 spec key 留痕（关键字必须引用，否则 unbound identifier）
    [_ (raise-parse ':memory-policy
                    (format "必需是 (:markdown-fs PATH :layers (…) :auto-append #t/#f)，得到 ~s" mp))]))

;; :status-bar 的取值允许两种写法：
;;   ① (:status-bar :step-count #t …)   自带标签
;;   ② (:step-count #t …)               裸 KV 列表（夹具/宏展开产物用这种）
(define (parse-status-bar sb)
  (define (build kvs)
    (let ([kw (keyword-kvs kvs '(:step-count :current-branch :test-status
                                          :time-tracker :todo-list))])
      (hash 'step_count    (->racket-bool (hash-ref kw ':step-count #t))
            'current_branch(->racket-bool (hash-ref kw ':current-branch #f))
            'test_status   (->racket-bool (hash-ref kw ':test-status #f))
            'time_tracker  (->racket-bool (hash-ref kw ':time-tracker #f))
            'todo_list     (->racket-bool (hash-ref kw ':todo-list #f))
            'custom (for/hash ([(k v) (in-hash (hash-remove-keys kw '(:step-count :current-branch
                                                                         :test-status :time-tracker :todo-list)))])
                      (values (to-str k) v)))))
  (cond
    [(not sb) (hash 'step_count #t 'current_branch #f 'test_status #f
                    'time_tracker #f 'todo_list #f 'custom (hash))]
    [(and (pair? sb) (eq? (car sb) ':status-bar)) (build (cdr sb))]
    [(list? sb) (build sb)]
    [else (raise-parse ':status-bar (format "必需是 (:status-bar …) 或 (:step-count …)，得到 ~s" sb))]))

;;; ---------- parse-tools (修复 MAJOR-5：支持 4 种组合：仅 builtin / 仅 mcp / 仅 define-tool / 任意组合) ----------
(define (parse-tools form)
  (match form
    [`(:tools . ,clauses)
     (let loop ([cs clauses] [builtins '()] [mcps '()] [define-tools '()])
       (cond
         [(null? cs)
          ;; 基例必须返回结果 hash：旧实现把 hash 写在 if 之后，递归返回值被丢弃，
          ;; 于是永远用初始空累加器构造结果 —— 工具字段恒为空（现代路径此前未被跑到，故未暴露）。
          (when (and (null? builtins) (null? mcps) (null? define-tools))
            (raise-parse ':tools "至少要有一种工具源（import-builtin / import-mcp / define-tool）"))
          (hash 'builtins builtins 'mcp_servers mcps 'define_tools define-tools)]
         [else
          (match (car cs)
             [`(import-builtin . ,names)
              (loop (cdr cs) (append builtins names) mcps define-tools)]
             [`(import-mcp ,url)
              (unless (string? url) (raise-parse ':tools "import-mcp URL 必须是字符串"))
              (loop (cdr cs) builtins (append mcps (list url)) define-tools)]
             [`(define-tool ,tool-name ,inputs ,outputs)
              (loop (cdr cs) builtins mcps
                    (append define-tools
                            (list (hash 'name (to-str tool-name)
                                        'inputs (map (lambda (kv) (list (to-str (car kv)) (to-str (cadr kv))))
                                                     inputs)
                                        'outputs outputs))))]
             [_ (raise-parse ':tools (format "未知 tools 子句：~s" (car cs)))])]))]
    [_ (raise-parse ':tools (format "必需是 (:tools …)，得到 ~s" form))]))

;;; ---------- parse-harness (修复 MAJOR-4/MAJOR-2；枚举值域) ----------
(define (parse-harness form)
  (match form
    [`(:harness ,constrain-clause ,verify-clause ,correct-clause)
     (hash 'constrain (parse-constrain constrain-clause)
           'verify    (parse-verify verify-clause)
           'correct   (parse-correct correct-clause))]
    [_ (raise-parse ':harness
                    (format "必需是 (:harness (:constrain …) (:verify …) (:correct …))，得到 ~s" form))]))

(define (parse-constrain c)
  (match c
    [`(:constrain . ,kvs)
     (let ([kw (keyword-kvs kvs '(:require-human-approval :forbidden-commands :workspace-root))])
       (hash 'require_human_approval
             (for/list ([a (in-list (hash-ref kw ':require-human-approval '()))])
               (to-str a))
             'forbidden_commands
             (for/list ([f (in-list (hash-ref kw ':forbidden-commands '()))])
               (unless (string? f) (raise-parse ':constrain "forbidden-commands 条目必须是字符串"))
               (when (string=? (string-trim f) "")
                 (raise-parse ':constrain "forbidden-commands 存在空串（会误杀所有命令）"))
               f)
             'workspace_root (let ([r (hash-ref kw ':workspace-root #f)]) (and r (to-str r)))))]
    [_ (raise-parse ':constrain (format "必需是 (:constrain …)，得到 ~s" c))]))

(define (parse-verify v)
  (match v
    [`(:verify . ,kvs)
     (let ([kw (keyword-kvs kvs '(:json-schema :linter-check :test-runner :reviewer-agent))])
       (define tr (hash-ref kw ':test-runner #f))
       (when (and tr (not (string? tr)))
         (raise-parse ':verify (string-append ":test-runner 必须是字符串（如 \"pytest tests/\"）；符号会导致 Python SyntaxError，得到：" (to-str tr))))
       (hash 'json_schema (->racket-bool (hash-ref kw ':json-schema #f))
             'linter_check (->racket-bool (hash-ref kw ':linter-check #f))
             'test_runner (and tr tr)
             'reviewer_agent (let ([a (hash-ref kw ':reviewer-agent #f)]) (and a (to-str a)))))]
    [_ (raise-parse ':verify (format "必需是 (:verify …)，得到 ~s" v))]))

(define (parse-correct c)
  (match c
    [`(:correct . ,kvs)
     (let ([kw (keyword-kvs kvs '(:max-retries :circuit-breaker :on-failure))])
       (define retries (hash-ref kw ':max-retries 3))
       (define breaker (hash-ref kw ':circuit-breaker 5))
       (define on-fail (unwrap-quote (hash-ref kw ':on-failure 'ask-human)))
       (unless (and (integer? retries) (> retries 0) (<= retries 10))
         (raise-parse ':correct ":max-retries 必须 1..10 的整数"))
       (unless (and (integer? breaker) (> breaker 0))
         (raise-parse ':correct ":circuit-breaker 必须是正整数"))
       (unless (enum-member? on-fail CORRECT-ON-FAILURE-ENUM)
         (raise-parse ':correct (format ":on-failure 枚举=~a，得到 ~a" CORRECT-ON-FAILURE-ENUM on-fail)))
       (hash 'max_retries retries
             'circuit_breaker breaker
             'on_failure (to-str on-fail)))]
    [_ (raise-parse ':correct (format "必需是 (:correct …)，得到 ~s" c))]))

;;; ---------- parse-multi (修复 MAJOR-9：MultiAgentBlock + scoped-worker) ----------
(define (parse-multi m)
  (match m
    [`(:multiagent :topology ,topology :workers ,workers)
     (define topology* (unwrap-quote topology))
     (unless (enum-member? topology* TOPOLOGY-ENUM)
       (raise-parse ':multiagent (format ":topology 枚举=~a，得到 ~a" TOPOLOGY-ENUM topology)))
     (hash 'topology (to-str topology*)
           'workers (for/list ([w workers]) (parse-scoped-worker w)))]
    [_ (raise-parse ':multiagent
                    (format "必需是 (:multiagent :topology … :workers ((scoped-worker …) …))，得到 ~s" m))]))

(define (parse-scoped-worker w)
  (match w
    [`(scoped-worker ,name
       (:model :provider ,p :name ,mn :temperature ,t :system-prompt ,sp)
       (:tools . ,tools-clauses)
       (:harness ,c ,v ,co))
     (hash 'name (to-str name)
           'model (parse-model `(:model :provider ,p :name ,mn :temperature ,t :system-prompt ,sp))
           'tools (parse-tools `(:tools ,@tools-clauses))
           'harness (parse-harness `(:harness ,c ,v ,co)))]
    [`(scoped-worker ,name
       (:model :provider ,p :name ,mn :system-prompt ,sp)
       (:tools . ,tools-clauses)
       (:harness ,c ,v ,co))
     (parse-scoped-worker `(scoped-worker ,name
                              (:model :provider ,p :name ,mn :temperature 0.2 :system-prompt ,sp)
                              (:tools ,@tools-clauses)
                              (:harness ,c ,v ,co)))]
    [_ (raise-parse 'scoped-worker (format "scoped-worker 子句不合法：~s" w))]))

;;; ---------- keyword KV 辅助：把 (:k1 v1 :k2 v2 …) 解析成 hash ----------
;; AgentLisp DSL 里的 :key 是**符号**（symbol），不是 Racket keyword（#:key）——
;; 原实现用 (keyword? …) 判断，恒为 #f，导致任何合法 KV 块都报"KV 不合法"。
(define (dsl-key? x)
  (and (symbol? x)
       (let ([s (symbol->string x)])
         (and (> (string-length s) 0) (char=? (string-ref s 0) #\:)))))

(define (keyword-kvs kvs allowed)
  (let loop ([xs kvs] [out (hash)])
    (cond
      [(null? xs) out]
      [(or (null? (cdr xs)) (not (dsl-key? (car xs))))
       (raise-parse 'keyword-kvs (format "KV 不合法（期望 :KEY VAL …），残余：~s" xs))]
      [else
       (define k (car xs))
       (when allowed (unless (memq k allowed)
                       (raise-parse 'keyword-kvs (format "未知关键字 ~a；允许=~a" k allowed))))
       (loop (cddr xs) (hash-set out k (cadr xs)))])))

(define (hash-remove-keys h ks)
  (for/fold ([h h]) ([k (in-list ks)])
    (if (hash-has-key? h k) (hash-remove h k) h)))

;; =====================================================================
;; 2. CHECKER  §4 三条 ERR_ + shape —— 实现统一迁移到 checker.rkt（关注点分离）
;;   check-agent / check-kv-alignment-order / check-unguarded-tool-execution /
;;   check-context-leakage / check-shapes 全部由 (require "checker.rkt") 提供
;; =====================================================================

;; =====================================================================
;; 3. EMITTER  BaseHarnessV2 子类 + HARNESS_REGISTRY（修复 MINOR-13/14 CRIT-2 MAJOR-1）
;; =====================================================================

;; 单 agent 的产物主体（不含文件头）。文件头单独生成，因为指纹要盖全文件。
(define (agent->py-body parsed)
  (define name (to-str (hash-ref parsed 'name)))
  (define cls-name (string-append (pascal-case name) "Harness"))
  (define model (hash-ref parsed 'model))
  (define ctx (hash-ref parsed 'context))
  (define tools (hash-ref parsed 'tools))
  (define harness (hash-ref parsed 'harness))
  (define multi (hash-ref parsed 'multi #f))
  (string-append
   (emit-model-dict model)
   (emit-context-dict ctx)
   (emit-tools-config tools)
   (emit-patterns-dict parsed)
   (emit-evolution-dict parsed)
   (emit-state-dict parsed)
   (emit-workflow-dict parsed)
   (emit-harness-dict harness)
   (emit-init-footer cls-name)
   (emit-build-kv-aligned-context-hook)
   (emit-constrain-method harness)
   (emit-run-react-loop-stub)
   (emit-harness-registry cls-name name)))

;; CR-42：模式落到语言层。产物里出现 PATTERNS 列表（由注册表生成），
;; 不再只把模式语义写在 system-prompt 文本里 —— 这样模式可被静态断言与运行时读取。
(define (emit-patterns-dict parsed)
  (define pats (hash-ref parsed 'patterns '()))
  (string-append
   ;; 注意：本段落在 __init__ 内（8 空格缩进），与 model/context/tools 同级
   "        # CR-42 patterns (generated from compiler/pattern_registry.rkt)\n"
   (format "        self.PATTERNS: List[Dict[str, Any]] = [~a]\n\n"
           (string-join (for/list ([p (in-list pats)])
                          (registry-emit (hash-ref p 'kind)
                                         (hash-ref p 'config (hash))))
                        ", "))))

;; RSI 契约 §5.1：产物携带 EVOLUTION，供离线 Evolver 读取；
;; 没有 (:evolution …) 时显式写 None，避免运行期属性缺失。
(define (emit-evolution-dict parsed)
  (define evo (hash-ref parsed 'evolution #f))
  (define body
    (if evo
        (format (string-append "{'online_trace': ~a, 'offline_evolver': ~a, "
                               "'mutation_targets': [~a], "
                               "'immutable_invariants': [~a], "
                               "'verifier_gate': {'name': ~a, 'min_pass_rate': ~a, "
                               "'mcnemar_p_threshold': ~a}}")
                (if (hash-ref evo 'online-trace #f) "True" "False")
                (py-string (hash-ref evo 'offline-evolver ""))
                (string-join (for/list ([t (in-list (hash-ref evo 'mutation-targets))])
                               (py-string (symbol->string t)))
                             ", ")
                (string-join (for/list ([i (in-list (hash-ref evo 'immutable-invariants))])
                               (py-string (symbol->string i)))
                             ", ")
                (py-string (hash-ref (hash-ref evo 'verifier-gate) 'name))
                (hash-ref (hash-ref evo 'verifier-gate) 'min-pass-rate)
                (hash-ref (hash-ref evo 'verifier-gate) 'mcnemar-p-threshold))
        "None"))
  (format "        # RSI evolution contract (spec §5.1)\n        self.EVOLUTION: Dict[str, Any] = ~a\n\n" body))

;; F-AMS-3（US-04）：产物带 STATE_FIELDS，运行期可读。没有 :state 时显式空 dict。
(define (py-literal v)
  (cond [(boolean? v) (if v "True" "False")]
        [(string? v) (py-string v)]
        [(integer? v) (number->string v)]
        [(real? v) (number->string (exact->inexact v))]
        [(symbol? v) (py-string (symbol->string v))]
        [(null? v) "None"]
        [(list? v) (string-append "[" (string-join (map py-literal v) ", ") "]")]
        [else (py-string (to-str v))]))

(define (emit-state-dict parsed)
  (define st (hash-ref parsed 'state #f))
  (define body
    (if st
        (format "{~a}"
                (string-join
                 (for/list ([f (in-list (hash-ref st 'fields))])
                   (string-append
                    (py-string (hash-ref f 'name))
                    ": {'type': "
                    (py-string (hash-ref f 'type))
                    (if (hash-ref f 'has-default)
                        (string-append ", 'default': " (py-literal (hash-ref f 'default)))
                        "")
                    "}"))
                 ", "))
        "{}"))
  (format (string-append
           "        # F-AMS-3 state fields (US-04)\n"
           "        self.STATE_FIELDS: Dict[str, Any] = ~a\n\n")
          body))

;; F-AMS-1（US-05）：产物带 WORKFLOW（入口 + 节点表 + 边表 + 环表），运行期可读。
(define (emit-workflow-dict parsed)
  (define wf (hash-ref parsed 'workflow #f))
  (define body
    (if wf
        (format "{'entry': ~a, 'nodes': [~a], 'edges': [~a], 'loops': [~a]}"
                (py-string (hash-ref wf 'entry))
                (string-join
                 (for/list ([n (in-list (hash-ref wf 'nodes))])
                   (format (string-append
                            "{'name': ~a, 'type': ~a, 'handler': ~a, "
                            "'static': ~a, 'dynamic': ~a, 'output_fields': [~a], "
                            "'effect': ~a, 'isolation': ~a}")
                           (py-string (hash-ref n 'name))
                           (py-string (hash-ref n 'type))
                           (if (hash-ref n 'handler)
                               (py-string (hash-ref n 'handler))
                               "None")
                           (py-string (hash-ref n 'static '""))
                           (py-string (hash-ref n 'dynamic '""))
                           (string-join (map py-string (hash-ref n 'outputs '())) ", ")
                           (py-string (hash-ref n 'effect 'pure))
                           (py-string (hash-ref n 'isolation ""))))
                 ", ")
                (string-join
                 (for/list ([ed (in-list (hash-ref wf 'edges))])
                   (format "{'from': ~a, 'to': ~a, 'kind': ~a}"
                           (py-string (hash-ref ed 'from))
                           (py-string (hash-ref ed 'to))
                           (py-string (hash-ref ed 'kind))))
                 ", ")
                (string-join
                 (for/list ([l (in-list (hash-ref wf 'loops))])
                   (format "{'nodes': [~a], 'while': ~a, 'max_rounds': ~a}"
                           (string-join (map py-string (hash-ref l 'nodes)) ", ")
                           (py-string (hash-ref l 'while))
                           (hash-ref l 'max-rounds)))
                 ", "))
        "None"))
  (format (string-append
           "        # F-AMS-1 workflow graph (US-05)\n"
           "        self.WORKFLOW: Dict[str, Any] = ~a\n\n")
          body))

(define (emit-header parsed)
  (define cls-name (string-append (pascal-case (to-str (hash-ref parsed 'name))) "Harness"))
  (define agent-name (to-str (hash-ref parsed 'name)))
  (string-append
   "# -*- coding: utf-8 -*-\n"
   "# Generated by Racket AgentLisp Compiler (spec v2.0 对齐)\n"
   "# Formula: Agent = Model + Harness\n"
   "#\n"
   "# 【机器拦】不要手工改本文件。本文件由编译器生成，重编译会整文件覆盖。\n"
   "# 下面这行是**本文件全内容**的 sha256 指纹（计算时本字段置空）。\n"
   "# 重编译前编译器把「本文件」与「本次将写入的文本」规范化后逐字节比对：\n"
   "# 不一致 = 上次生成后有人手工改过 →\n"
   "# 拒绝覆盖并给出退出码 3（可用 --force 强制覆盖）。\n"
   "# 手工逻辑请写在使用方自己的子类/包装里，不要写进本文件。\n"
   ;; __future__ 必须在所有语句之前（含下面的 sha256 赋值）——否则产物 SyntaxError。
   ;; 台账 #38：自审用端到端测试（编译→import 产物）才发现，手工设 PATTERNS 的单测漏掉了它。
   "from __future__ import annotations\n\n"
   (format "~a = \"\"\n" CONTENT-SHA256-FIELD)
   "\n"
   "from typing import Any, Dict, List, Optional\n"
   "from runtime.base_harness_v2 import BaseHarnessV2, build_kv_aligned_context\n\n"
   (format "class ~a(BaseHarnessV2):\n" cls-name)
   (format "    agent_name = ~s\n" agent-name)
   (format "    AGENT_NAME = ~s\n\n" agent-name)
   "    def __init__(self, *args: Any, **kwargs: Any) -> None:\n"
   "        # 组装 spec 规定的四个一等 dict，传给 BaseHarnessV2 四参 constructor\n"
   ))

;; =====================================================================
;; drift 指纹：计算 / 提取 / 判定（一处实现，main.rkt 与校验脚本共用）
;; =====================================================================

;; 指纹口径：把指纹字段的值**置空**后再算 sha256。
;; 为什么置空：指纹不能包含自己，否则无法自洽计算。
(define (canonical-for-sha256 text)
  (regexp-replace* CONTENT-SHA256-PATTERN text
                   (string-append CONTENT-SHA256-FIELD " = \"\"")))

;; 单 agent 块（含头，指纹字段留空）—— 供 build-generated-python 拼装后统一计算指纹。
(define (agent->py-unsigned parsed)
  (string-append (emit-header parsed) (agent->py-body parsed)))

;; 把「留空指纹的文本」签上指纹。
(define (sign-content unsigned-text digest)
  (regexp-replace* CONTENT-SHA256-PATTERN unsigned-text
                   (string-append CONTENT-SHA256-FIELD " = \"" digest "\"")))

;; 计算「留空指纹的文本」应有的指纹。
(define (digest-of-unsigned unsigned-text)
  (sha256-hex (canonical-for-sha256 unsigned-text)))

;; 组装完整产物：N 个 agent 块，每块头部签上**同一个**「全文件」指纹。
;; 为什么全文件而非分块：
;;   1. drift 判定的对象是磁盘上那个文件，不是某一段；
;;   2. 逐块签名（每块签自己）会自相矛盾 —— 块 A 的指纹算不到块 B，
;;      而「重编译后看到的文件」是 A+B，比对必然不等 → 永远假漂移。
;;      （实测 2026-10-14：多 agent 文件第二块起 drift 判定必错。）
(define (content-digest-of-agents parsed-agents)
  (digest-of-unsigned (string-join (map agent->py-unsigned parsed-agents) "\n")))

(define (build-generated-python parsed-agents)
  (unless (pair? parsed-agents)
    (error 'build-generated-python "至少需要一个已解析的 agent"))
  (sign-content (string-join (map agent->py-unsigned parsed-agents) "\n")
                (content-digest-of-agents parsed-agents)))

;; 给任意「留空指纹」文本签上它自己的指纹。
;; 用于多 agent：先按所需格式拼装，再签上全文件指纹。
(define (signed-content-of unsigned-text)
  (sign-content unsigned-text (digest-of-unsigned unsigned-text)))

;; 单 agent 产物（对外保持 agent->py 的兼容签名）。
(define (agent->py parsed)
  (build-generated-python (list parsed)))

;; 磁盘文件是否被手工改过？判定基准 = 本次**准备写入**的完整文本。
;; 返回 'clean | 'drifted | 'unmarked。
;; 口径：
;;   · 文件不存在 / 无**已签名**指纹 → 'unmarked（不是 drift，可自由写）
;;   · 已签名指纹 == 本次将写入的指纹 → 'clean
;;   · 已签名指纹 != 本次将写入的指纹 → 'drifted（拒绝覆盖，exit 3）
;; 从产物文本里提取已签名指纹。无指纹（旧产物 / 手写文件 / 未签名）→ #f。
(define (embedded-content-sha256 text)
  (define m (regexp-match CONTENT-SHA256-SIGNED-PATTERN text))
  (and m (list-ref m 1)))

;; 磁盘文件是否被手工改过？判定基准 = 本次**准备写入**的完整文本。
;; 返回 'clean | 'drifted | 'unmarked。
;; 口径（比对的是「规范化后的全文」，不是「头部那个指纹字符串」）：
;;   把两边的指纹字段都置空，然后逐字节比对全文。
;;   · 文件不存在 / 无已签名指纹 → 'unmarked（旧产物或手写文件，可自由写）
;;   · 规范化(磁盘) == 规范化(本次生成) → 'clean
;;   · 否则 → 'drifted
;; 为什么比对全文而不比对指纹字符串：
;;   只比指纹字符串时，**尾部追加的内容不进入比较** —— 实测（2026-10-14）
;;   往产物末尾追加一行「手工加的一行」，只读校验照样报 CLEAN。
;;   指纹必须覆盖它声称覆盖的全部内容，否则它是装饰品，不是闸门。
(define (file-content-drifted? path generated-text)
  (define f (if (path? path) path (string->path path)))
  (cond
    [(not (file-exists? f)) 'unmarked]
    [else
     (define disk (file->string f))
     (cond
       [(not (embedded-content-sha256 disk)) 'unmarked]
       [(string=? (canonical-for-sha256 disk) (canonical-for-sha256 generated-text)) 'clean]
       [else 'drifted])]))

(define (emit-model-dict m)
  (define sys (py-string (hash-ref m 'system_prompt)))
  (format #<<EOS
        model_config: Dict[str, Any] = {
            'provider': ~v,
            'name': ~v,
            'temperature': ~a,
            'system_prompt': ~a,
            'agent_name': ~v,
        }

EOS
          (hash-ref m 'provider)
          (hash-ref m 'name)
          (format "~a" (hash-ref m 'temperature))
          sys
          (hash-ref m 'name)))

(define (emit-context-dict ctx)
  (define mp (hash-ref ctx 'memory_policy #f))
  (define layers (if mp (py-list/str (hash-ref mp 'layers)) "[]"))
  (define sb (hash-ref ctx 'status_bar))
  (format #<<EOS
        context_config: Dict[str, Any] = {
            'markdown_fs': ~v,
            'layers': ~a,
            'auto_append_episodic': ~a,
            'skills': ~a,
            'status_bar': {
                'step_count': ~a,
                'current_branch': ~a,
                'test_status': ~a,
                'time_tracker': ~a,
                'todo_list': ~a,
                'custom': ~a,
            },
            'compression': ~v,
        }

EOS
          (if mp (hash-ref mp 'path) "None")
          layers
          (if mp (py-bool (hash-ref mp 'auto_append_episodic)) "False")
          (py-list/str (hash-ref ctx 'skills))
          (py-bool (hash-ref sb 'step_count))
          (py-bool (hash-ref sb 'current_branch))
          (py-bool (hash-ref sb 'test_status))
          (py-bool (hash-ref sb 'time_tracker))
          (py-bool (hash-ref sb 'todo_list))
          (py-dict-str (hash-ref sb 'custom (hash)))
          (let ([c (hash-ref ctx 'compression #f)]) (if c (to-str c) "None"))))

(define (emit-tools-config tools)
  (define builtins (py-list/str (map to-str (hash-ref tools 'builtins '()))))
  (define mcp      (py-list/str (hash-ref tools 'mcp_servers '())))
  (define defs     (for/list ([t (in-list (hash-ref tools 'define_tools '()))])
                     (format "{'name': ~s, 'inputs': ~a}"
                             (hash-ref t 'name)
                             (py-list/str (for/list ([x (hash-ref t 'inputs)])
                                            (format "{'name': ~s, 'type': ~s}" (car x) (cadr x)))))))
  (define tools-schema
    (string-join
     `(,@(if (null? (hash-ref tools 'builtins '()))
            '()
            (list (format "Builtins: ~a" builtins)))
       ,@(if (null? (hash-ref tools 'mcp_servers '()))
             '()
             (list (format "MCP servers: ~a" mcp)))
       ,@(if (null? (hash-ref tools 'define_tools '()))
             '()
             (list (format "Custom tools (count=~a)" (length defs)))))
     "\n"))
  (define defs-dump
    (if (null? defs) "[]" (string-append "[" (string-join defs ", ") "]")))
  (format #<<EOS
        tools_config: Dict[str, Any] = {
            'tools_schema': ~a,
            'import_builtins': ~a,
            'mcp_servers': ~a,
            'define_tools': ~a,
        }
        self.tools = {
            'builtins': ~a,
            'mcp_servers': ~a,
            'define_tools': ~a,
        }

EOS
          (py-string tools-schema)
          builtins
          mcp
          defs-dump
          builtins
          mcp
          defs-dump))

(define (emit-harness-dict h)
  (define c (hash-ref h 'constrain))
  (define v (hash-ref h 'verify))
  (define co (hash-ref h 'correct))
  (format #<<EOS
        harness_config: Dict[str, Any] = {
            'constrain': {
                'require_approval': ~a,
                'forbidden_commands': ~a,
                'workspace_root': ~v,
                '_matching': 'token_boundary',
            },
            'verify': {
                'json_schema': ~a,
                'linter_check': ~a,
                'test_runner': ~v,
                'reviewer_agent': ~v,
            },
            'correct': {
                'max_retries': ~a,
                'circuit_breaker': ~a,
                'on_failure': ~v,
            },
        }

EOS
          (py-list/str (hash-ref c 'require_human_approval))
          (py-list/str (hash-ref c 'forbidden_commands))
          (or (hash-ref c 'workspace_root) "None")
          (py-bool (hash-ref v 'json_schema))
          (py-bool (hash-ref v 'linter_check))
          (or (hash-ref v 'test_runner) "None")
          (or (hash-ref v 'reviewer_agent) "None")
          (number->string (hash-ref co 'max_retries))
          (number->string (hash-ref co 'circuit_breaker))
          (hash-ref co 'on_failure)))

(define (emit-multi-class-vars multi)
  (if (not multi)
      "        _multi_topology = None\n        _multi_workers = []\n\n"
      (let ([top (hash-ref multi 'topology)]
            [ws (for/list ([w (in-list (hash-ref multi 'workers))])
                  (format "{'name': ~s, 'model_provider': ~s, 'on_failure': ~s}"
                          (hash-ref w 'name)
                          (hash-ref (hash-ref w 'model) 'provider)
                          (hash-ref (hash-ref (hash-ref w 'harness) 'correct) 'on_failure)))])
        (format #<<EOS
        _multi_topology = ~v
        _multi_workers = [~a]

EOS
                top
                (string-join ws ", ")))))

(define (emit-init-footer cls-name)
  (format #<<EOS
        super().__init__(
            model_config=model_config,
            context_config=context_config,
            tools_config=tools_config,
            harness_config=harness_config,
            agent_name=self.agent_name,
            *args,
            **kwargs,
        )

EOS
          ))

(define (emit-build-kv-aligned-context-hook)
  ;; 兼容旧签名：BaseHarnessV2.build_context() 是无参版本，这里允许可选 trajectory。
  ;; 关键修复：不再复制一份四段拼装实现。旧实现在此处漏了 patterns.before_turn / order，
  ;; 编译产物（端到端用户路径）因此看不到模式注入 —— 单测手工设 PATTERNS 时发现不了。
  ;; 一处判断只留一处实现：拼装与模式注入都委托给基类。
  #<<EOS
    def build_context(self, trajectory=None):
        if trajectory is None:
            return super().build_context()
        _saved = self.trajectory
        self.trajectory = trajectory
        try:
            return super().build_context()
        finally:
            self.trajectory = _saved

EOS
  )

(define (emit-constrain-method harness)
  ;; 修复 MAJOR-1：子串误杀 → word boundary；与 runtime._contains_forbidden_token 等价但独立实现
  #<<EOS
    def constrain(self, tool_call):
        import re
        args = tool_call.get('args', {}) or {}
        cmd = str(args.get('command', ''))
        forbidden_list = list(self.harness_config['constrain'].get('forbidden_commands', []) or [])

        def _contains(cmd: str, forbidden: str) -> bool:
            try:
                import shlex as _shlex
                tokens = _shlex.split(cmd, comments=True, posix=True)
            except ValueError:
                tokens = []
            ft = forbidden.split()
            if tokens:
                if len(ft) == 1 and ft[0] in tokens:
                    return True
                for i in range(len(tokens) - len(ft) + 1):
                    if tokens[i:i+len(ft)] == ft:
                        return True
            pat = r'(?<![A-Za-z0-9_./-])' + re.escape(forbidden) + r'(?![A-Za-z0-9_./-])'
            return bool(re.search(pat, cmd))

        for forbidden in forbidden_list:
            if forbidden and _contains(cmd, forbidden):
                return False, f"Harness Blocked: Execution of {forbidden!r} is strictly forbidden."
        return True, 'OK'

EOS
  )

(define (emit-run-react-loop-stub)
  #<<EOS
    def run_react_loop(self, user_input: str = ''):
        """Legacy 兼容钩子：新代码请使用 BaseHarnessV2.run(user_input) / step() / stream_async"""
        import asyncio
        return asyncio.run(self.run(user_input))

EOS
  )

(define (emit-harness-registry cls-name agent-name)
  (format #<<EOS


AGENT_NAME = ~v
HARNESS_REGISTRY = {~v: ~a}

__all__ = ['AGENT_NAME', 'HARNESS_REGISTRY', ~v]


if __name__ == '__main__':
    import json as _json
    print(_json.dumps({'module': __name__, 'agents': [AGENT_NAME]}, ensure_ascii=False))
EOS
          agent-name
          agent-name
          cls-name
          cls-name))

(define (py-dict-str h)
  (string-append "{"
                 (string-join
                  (for/list ([(k v) (in-hash h)])
                    (format "~s: ~s" (to-str k) (to-str v)))
                  ", ")
                 "}"))

;; =====================================================================
;; 4. 对外统一入口：compile-agent-lisp（parse + check + emit）
;; =====================================================================

(define (compile-agent-lisp agent-ast #:mode [mode 'full])
  (define parsed (parse-defagent agent-ast))
  (define checked (check-agent parsed))
  (case mode
    [(parse)  parsed]
    [(check)  checked]
    [(full emit) (agent->py checked)]
    [else (raise-argument-error 'compile-agent-lisp "#:mode ∈ {parse, check, full, emit}" mode)]))

;; =====================================================================
;; 示例测试：sample-agent-lisp 直接编译（spec §5 推荐值样例）
;; =====================================================================
(module+ main
  (define sample-agent-lisp
    '(defagent code-repair-agent
       (:model :provider "anthropic"
               :name "claude-3-7-sonnet"
               :temperature 0.2
               :system-prompt "你是一个严谨的 Coding Agent。")
       (:context :memory-policy (:markdown-fs "./workspace"
                                 :layers (L0-Abstract L1-Overview L2-FullText)
                                 :auto-append #t)
                 :skills (python-debugging git-worktree-management)
                 :status-bar (:step-count #t :current-branch #t :test-status #t
                                          :time-tracker #t :todo-list #t))
       (:tools (import-builtin read-file edit-file bash grep)
               (import-mcp "mcp://github-server/tools"))
       (:harness (:constrain :require-human-approval (git-push)
                             :forbidden-commands ("rm -rf" "git reset --hard"))
                 (:verify :json-schema #t :linter-check #t :test-runner "pytest tests/")
                 (:correct :max-retries 3 :circuit-breaker 5 :on-failure ask-human))))

  (displayln (compile-agent-lisp sample-agent-lisp)))
;; BASH-WRITE-PROBE
