#lang racket/base

(require racket/string
         racket/hash)

;; =============================================================================
;; CR-42 模式注册表（Pattern Registry）
;;
;; 一个模式 = 一条数据。加模式只改本文件，不改 parser / checker / emitter 的分支。
;; Core AST 只新增唯一构造 (:pattern (:kind K) (:config …))；K 取值来自本表。
;; =============================================================================

(provide pattern-kinds
         registry-lookup
         registry-validate-config
         registry-unknown-keys
         registry-emit
         validate-pattern-block)

(struct registry-entry (kind required schema emit doc)
  #:transparent)

(define *registry* (make-hash))

(define (define-pattern! e)
  (hash-set! *registry* (registry-entry-kind e) e))

(define (pattern-kinds)
  (sort (hash-keys *registry*) symbol<?))

(define (registry-lookup kind)
  (hash-ref *registry* kind #f))

;; 常用 schema 谓词（racket/base 无 positive-integer?）
(define (positive-integer? v) (and (integer? v) (> v 0)))

;; ---------- Python 字面量小工具 ----------
;; 用字符码构造反斜杠与双引号，避免源码里出现转义序列。
(define BS (string (integer->char 92)))
(define DQ (string (integer->char 34)))
(define NL (integer->char 10))
(define TAB (integer->char 9))

(define (py-str s)
  (define out (open-output-string))
  (write-string DQ out)
  (for ([c (in-string s)])
    (cond
      [(char=? c (integer->char 34)) (write-string (string-append BS DQ) out)]
      [(char=? c (integer->char 92)) (write-string (string-append BS BS) out)]
      [(char=? c NL) (write-string (string-append BS "n") out)]
      [(char=? c TAB) (write-string (string-append BS "t") out)]
      [else (write-char c out)]))
  (write-string DQ out)
  (get-output-string out))

(define (py-value v)
  (cond
    [(string? v) (py-str v)]
    [(boolean? v) (if v "True" "False")]
    [(integer? v) (number->string v)]
    [(real? v) (number->string (exact->inexact v))]
    [(and (list? v) (andmap string? v)) (string-append "[" (string-join (map py-str v) ", ") "]")]
    [(symbol? v) (py-str (symbol->string v))]
    [else (py-str (format "~a" v))]))

;; ---------- 校验：返回错误字符串列表；空 = 合法 ----------

(define (registry-validate-config kind cfg)
  (define e (registry-lookup kind))
  (cond
    [(not e) (list (format "未知模式 kind=~a；已注册：~a" kind (pattern-kinds)))]
    [(not (hash? cfg)) (list (format ":config 必须是 (:key value …) 形式，得到 ~a" cfg))]
    [else
     (append
      (for/list ([k (in-list (registry-entry-required e))]
                 #:unless (hash-has-key? cfg k))
        (format "缺少必需 config 键 :~a" k))
      (for/list ([(k pred) (in-hash (registry-entry-schema e))]
                 #:when (hash-has-key? cfg k)
                 #:unless (pred (hash-ref cfg k)))
        (format "config 键 :~a 类型不符（得到 ~a）" k (hash-ref cfg k))))]))

;; 语义校验：config 里出现了 schema 与 required 之外的键（抓拼写错误）
(define (registry-unknown-keys kind cfg)
  (define e (registry-lookup kind))
  (cond
    [(not e) (list kind)]
    [else
     (for/list ([k (in-hash-keys cfg)]
                #:unless (or (memq k (registry-entry-required e))
                             (hash-has-key? (registry-entry-schema e) k)))
       k)]))

;; 校验来自 AST 的 (:pattern …) 块；返回 (values kind cfg errors)
(define (validate-pattern-block blk)
  (define (fail msg) (values #f #f (list msg)))
  (cond
    [(and (pair? blk) (eq? (car blk) ':pattern))
     (define body (cdr blk))
     (define (get key default)
       (let loop ([xs body])
         (cond [(null? xs) default]
               [(and (eq? (car xs) key) (pair? (cdr xs))) (cadr xs)]
               [else (loop (cddr xs))])))
     ;; AST 里的 :config 写作 (:key value …) plist，这里转成 hash 再校验
     (define (plist->hash xs)
       (let loop ([l xs] [h (hash)])
         (cond [(null? l) h]
               [(pair? (cdr l)) (loop (cddr l) (hash-set h (car l) (cadr l)))]
               [else h])))
     ;; 键归一化：AST 里写 :criteria，注册表里用 criteria（去掉前导冒号）
     (define (norm-key k)
       (define s (format "~a" k))
       (string->symbol (if (and (> (string-length s) 0) (char=? (string-ref s 0) #\:))
                           (substring s 1)
                           s)))
     (define (normalize raw)
       (define h (if (hash? raw) raw (plist->hash raw)))
       (for/hash ([(k v) (in-hash h)]) (values (norm-key k) v)))
     (define kind-raw (get ':kind #f))
     (cond
       [(not kind-raw) (fail "(:pattern …) 缺少 :kind")]
       [else
        (define kind (if (symbol? kind-raw) kind-raw (string->symbol (format "~a" kind-raw))))
        (define cfg (normalize (get ':config '())))
        ;; 宏把用户参数放 :params（不塞进 :config，避免任意键触发未知键错误）。
        ;; 只有本 kind 在注册表声明过的键才提升进 :config；其余保持 prompt-only。
        ;; 显式 (:config …) 里的未知键仍然报错（test_unknown_config_key_is_checker_error）。
        (define params (normalize (get ':params '())))
        (define e (registry-lookup kind))
        ;; 类型也要过：:params 是宽松的宏参数。只有键在注册表里有、且值过该键的谓词，
        ;; 才提升进 :config；否则保持 prompt-only。这样正向夹具里的宽松值
        ;; （如 fsm 的 (idle running done) 符号列表）不会被误判为 config 类型错。
        (define (promotable? k v)
          (and e
               (or (memq k (registry-entry-required e))
                   (hash-has-key? (registry-entry-schema e) k))
               (let ([pred (hash-ref (registry-entry-schema e) k #f)])
                 (or (not pred) (pred v)))))
        (define promoted
          (for/hash ([(k v) (in-hash params)] #:when (promotable? k v))
            (values k v)))
        ;; 显式 :config 优先：同键冲突取 cfg 的值（combine 的第二个参数）
        (define merged
          (hash-union promoted cfg #:combine (lambda (_from-params from-config) from-config)))
        (values kind merged (registry-validate-config kind merged))])]
    [else (fail (format "不是合法的模式块：~a" blk))]))

;; ---------- 生成（emitter 调用） ----------
(define (registry-emit kind cfg)
  (define e (registry-lookup kind))
  (if e
      ((registry-entry-emit e) cfg)
      (format "{'pattern': 'unknown', 'kind': ~a}" (py-str (format "~a" kind)))))

;; =============================================================================
;; 已注册模式
;; =============================================================================

;; 构造顺序：kind required schema emit doc（位置参数）
;;
;; 注意：这里**不**注册 priority。priority 的唯一注册点在下方 register-v2-pattern!。
;; 曾在此处有一份旧条目，被下方 V2 注册静默覆盖 —— 覆盖后 criteria 的 emit 分支变死代码，
;; 产物只剩 markers，运行时 PriorityHandler 因缺 criteria 起不来（CT-PRIORITY-01 违约）。
;; 一处判断只留一处实现：kind 的 schema 以 V2 注册为准。

;; =============================================================================
;; CR-42 P-2：V2 十宏对应的 kind
;; 语义（markers）从生成器单一事实源进入 AST 的 :config，不再只写在 system-prompt 文本里。
;; =============================================================================

(define (string-list? v) (and (list? v) (andmap string? v)))

(define (register-v2-pattern! kind doc extra-schema)
  (define-pattern!
   (registry-entry
    kind
    '(markers)
    (hash-union (hash 'markers string-list?) extra-schema #:combine (lambda (a b) b))
    ;; 通用 emit：kind + markers + 本 kind 声明的额外键（schema 里有、cfg 里就发）。
    ;; 为什么必须发额外键：运行时 handler 从 spec 读它们（如 priority 读 criteria）。
    ;; 只发 markers = 声明有、消费无（违反不变式 I1）。
    ;; 键按符号名字典序输出，保证同输入同产物（不变式 I3：编译期确定性）。
    (lambda (cfg)
      (define extra-keys
        (sort (hash-keys extra-schema)
              (lambda (a b) (string<? (symbol->string a) (symbol->string b)))))
      (define extra-parts
        (for/list ([k (in-list extra-keys)] #:when (hash-has-key? cfg k))
          (format "'~a': ~a" k (py-value (hash-ref cfg k)))))
      (format "{'pattern': ~a, 'markers': [~a]~a}"
              (py-str (symbol->string kind))
              (string-join (map py-str (hash-ref cfg 'markers '())) ", ")
              (if (null? extra-parts)
                  ""
                  (string-append ", " (string-join extra-parts ", ")))))
    doc)))

;; 额外键只声明「这个 kind 允许出现什么」，避免语法再次封闭（未知键由 checker 拦）。
(register-v2-pattern! 'priority          "优先级排序：按 criteria 排序，levels 指定层数"
                      (hash 'criteria string? 'levels positive-integer?))
(register-v2-pattern! 'decomposition     "递归分解：max-depth 指定层数"
                      (hash 'max-depth positive-integer?))
(register-v2-pattern! 'fsm               "有限状态机：initial-state 与 states 声明状态集合"
                      (hash 'initial-state string? 'states string-list?))
(register-v2-pattern! 'evaluator         "评估器：thresholds 声明双阈值"
                      (hash 'thresholds string-list?))
(register-v2-pattern! 'topic-model       "主题建模：processor 指定子 Agent 名"
                      (hash 'processor string?))
(register-v2-pattern! 'decomposer        "结构化提取：schema-fields 声明字段类型检查"
                      (hash 'schema-fields string-list?))
(register-v2-pattern! 'guardrails-safety "护栏安全：hooks 声明三段钩子"
                      (hash 'hooks string-list?))
(register-v2-pattern! 'hitl              "人在环：approval-before 声明需批准的阶段"
                      (hash 'approval-before string-list?))
(register-v2-pattern! 'exception         "异常恢复：retries 与 backoff 声明重试策略"
                      (hash 'retries positive-integer? 'backoff real?))
(register-v2-pattern! 'exploration      "探索发现：budget 与 convergence 声明停止条件"
                      (hash 'budget positive-integer? 'convergence real?))


;; =============================================================================
;; CR-42 P-3：V1 五宏对应的 kind（patterns.rkt 的 HC/GENERIC 分支产出）
;; =============================================================================

(register-v2-pattern! 'reflect  "反思/自我纠错：失败进入反思—修正回路，reviewer-agent 复核"
                      (hash 'max-retries positive-integer?))
(register-v2-pattern! 'router   "路由：先判定意图再分发到 Worker"
                      (hash 'routes string-list?))
(register-v2-pattern! 'chain    "提示链：按给定顺序执行步骤，前一步输出注入后一步"
                      (hash 'steps string-list?))
(register-v2-pattern! 'parallel "并行化：分支同时拉起，轮次可交错，最后归并"
                      (hash 'branches string-list?))
(register-v2-pattern! 'planner  "规划：先出计划再执行，结束时报告完成度"
                      (hash 'plan-size positive-integer?))


;; =============================================================================
;; CR-42 P-3e：剩余 6 个模式（21/21 覆盖）
;; 说明：这 6 个模式当前没有专属宏，但语言层已可表达 —— 用户可直接写
;;   (:pattern :kind <K> :config (:markers (...)))
;; 其中工具使用/MCP/记忆管理/多智能体协作 四个模式由核心语法（:tools/:memory-policy/:multiagent）
;; 承载，另有 15 个模式由 V1/V2 宏产出。
;; =============================================================================

(register-v2-pattern! 'rag             "智能体化 RAG：先检索再生成，证据必须回填"
                      (hash 'retriever string?))
(register-v2-pattern! 'a2a             "智能体间通信：跨 Agent 消息协议与 Agent Card"
                      (hash 'protocol string?))
(register-v2-pattern! 'reasoning       "推理技术：显式推理结构（CoT / 树状探索）"
                      (hash 'strategy string?))
(register-v2-pattern! 'learning        "学习与适应：把反馈写回技能层"
                      (hash 'skill-dir string?))
(register-v2-pattern! 'resource-aware  "资源感知：按成本/时延选择模型档位"
                      (hash 'budget string?))
(register-v2-pattern! 'goal-setting    "目标设定与监控：目标、进度与偏差处理"
                      (hash 'goal string?))


;; =============================================================================
;; CR-42 后续：核心语法糖宏对应的 kind（规格 §3.3-12 记忆管理、§3.5-20 多智能体协作）
;; 这两个模式由核心语法承载，宏只封装默认值与形状。用自定义 emitter，
;; 把 :context-window-gc / :topology / :workers 这类关键参数带进产物。
;; =============================================================================

(define-pattern!
 (registry-entry 'memory
                 '(store)
                 (hash 'store string?
                       'context-window-gc positive-integer?
                       'layers string-list?)
                 (lambda (cfg)
                   (format "{'pattern': \"memory\", 'store': ~a, 'context_window_gc': ~a}"
                           (py-str (hash-ref cfg 'store))
                           (py-value (hash-ref cfg 'context-window-gc 8))))
                 "记忆管理：markdown-fs 三层加载，超限回收"))

(define-pattern!
 (registry-entry 'multi-agent
                 '(topology workers)
                 (hash 'topology symbol?
                       'workers string-list?)
                 (lambda (cfg)
                   (format "{'pattern': \"multi-agent\", 'topology': ~a, 'workers': [~a]}"
                           (py-str (symbol->string (hash-ref cfg 'topology)))
                           (string-join (map py-str (hash-ref cfg 'workers)) ", ")))
                 "多智能体协作：topology + workers 词法隔离"))

