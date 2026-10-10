#lang racket/base

;; =====================================================================
;; AgentLisp Checker (v2.0, spec/SRS 对齐版 + JSON 结构化错误导出)
;; 模块职责：纯函数 AST 静态检查，不做 IO / 不做代码生成
;; 严格实现 SRS §4 三大 Compiler Invariants：
;;   1. ERR_KV_ALIGNMENT_VIOLATION     —— 静态段（:model/:tools）必须在动态段（:context）之前
;;   2. ERR_UNGUARDED_TOOL_EXECUTION  —— 有副作用 builtin 必须有 constrain / verify 护栏
;;   3. ERR_CONTEXT_LEAKAGE           —— scoped-worker define-tools 与父级重名 = 词法泄漏
;; 附加：shape 断言（CORRECT on_failure 枚举 / topology / layer / provider 值域）
;; 新增 (v2-patch CR-2)：
;;   - raise-check 扩 source location / agent-name / hints 字段
;;   - exn:agentlisp:check->jsexpr → jsexpr（Racket hasheq，JSON 可序列化 shape）
;;   - checker-structured-errors-thunk → 捕获 checker/parse 异常并按 JSON 打印
;;   - parse 异常也通过 raise-parse-with-srcloc 走统一 shape（SRS §5.1 --json-errors）
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
         exn:agentlisp:check-code
         exn:agentlisp:check-srcloc
         exn:agentlisp:check-agent-name
         exn:agentlisp:check-hints
         raise-check
         with-srcloc-from-form
         current-checker-source-name

         ;; JSON 结构化错误：--json-errors（SRS §5.1 CLI）
         exn->jsexpr
         exn:agentlisp:check->jsexpr
         checker-errors->jsexpr-list-thunk
         checker-default-jsexpr-version

         ;; Parse 异常也支持同样的 JSON shape（parser 使用 raise-parse-with-srcloc）
         exn:agentlisp:parse?
         exn:agentlisp:parse-code
         exn:agentlisp:parse-al-srcloc
         exn:agentlisp:parse-agent-name
         exn:agentlisp:parse-hints
         raise-parse-with-srcloc

         ;; 通用辅助
         to-str
         enum-member?)

(require racket/string
         racket/list
         racket/match
         json)

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
(define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push wget curl scp dd chmod sudo))

(define (enum-member? v lst [->id to-str])
  (for/or ([x (in-list lst)]) (string=? (->id v) (->id x))))

;; ---------------- 源位置（srcloc 推导 / 参数）------------------------
;; 当前 checker 正在看的源文件名（由 parser 或 main 传进来；#f 则 unknown）
(define current-checker-source-name
  (make-parameter #f
    (lambda (v)
      (cond
        [(or (not v) (string? v) (path? v)) v]
        [else (to-str v)]))
    'current-checker-source-name))

;; Racket 8.12: #:transparent 与 #:prefab 互斥（"multiple #:inspector/#:transparent/#:prefab
;; specifications"），同时出现会让本模块加载即失败。
;; 选择保留 #:transparent、去掉 #:prefab：prefab 结构体要求字段可 prefab 序列化，
;; 而 srcloc* 的字段来自任意 form（含 syntax/哈希等），实测会让 parse-defagent 直接
;; "invalid memory reference" 崩溃。透明结构体已满足 equal?/struct->vector 需求。
(struct srcloc* (source line column position span) #:transparent)

(define (srcloc*-from-form form [maybe-src (current-checker-source-name)] [pos-hint #f])
  (with-handlers ([exn:fail? (lambda (_) (srcloc* (or maybe-src "unknown") #f #f #f #f))])
    (define-values (src line col pos span)
      (cond
        [(syntax? form)
         (values (or (syntax-source form) maybe-src)
                 (syntax-line form)
                 (syntax-column form)
                 (syntax-position form)
                 (syntax-span form))]
        [pos-hint
         (values maybe-src
                 (hash-ref pos-hint 'line #f)
                 (hash-ref pos-hint 'column #f)
                 (hash-ref pos-hint 'position #f)
                 (hash-ref pos-hint 'span #f))]
        [else (values (or maybe-src "unknown") #f #f #f #f)]))
    (srcloc* (cond [(string? src) src] [(path? src) (path->string src)] [else (to-str src)])
             line col pos span)))

(define-syntax-rule (with-srcloc-from-form form-expr body0 body ...)
  (parameterize ([current-checker-source-name
                  (cond
                    [(syntax? form-expr)
                     (let ([src (syntax-source form-expr)])
                       (cond [(path? src) (path->string src)] [(string? src) src] [else #f]))]
                    [(string? form-expr) form-expr]
                    [(path? form-expr) (path->string form-expr)]
                    [else (current-checker-source-name)])])
    body0 body ...))

;; ------------------------------ 异常 --------------------------------
(struct exn:agentlisp:check exn:fail
  (code           ; symbol?，如 'ERR_KV_ALIGNMENT_VIOLATION
   srcloc         ; (or/c #f srcloc*?) — 源位置（未知则 #f）
   agent-name     ; (or/c #f string?) — 触发异常的 agent / scoped-worker 名
   hints          ; (listof string?) — 修复 hint，SRS §5.1 errors[].hints[]
   )
  #:transparent
  #:extra-constructor-name make-exn:agentlisp:check
  #:guard (lambda (msg cm code src an hints name)
            (define msg* (if (string? msg) msg (format "~a" msg)))
            (unless (symbol? code)
              (raise-argument-error 'exn:agentlisp:check "symbol? code" code))
            (unless (or (not src) (srcloc*? src))
              (raise-argument-error 'exn:agentlisp:check "(or/c #f srcloc*?) srcloc" src))
            (unless (or (not an) (string? an))
              (raise-argument-error 'exn:agentlisp:check "(or/c #f string?) agent-name" an))
            (unless (and (list? hints) (andmap string? hints))
              (raise-argument-error 'exn:agentlisp:check "(listof string?) hints" hints))
            (values msg* cm code src an hints)))

;; raise-check 调用栈约定：
;;   (raise-check 'ERR_X "msg" #:srcloc (srcloc*-from-form FORM) #:agent-name "a" #:hints '("hint"))
(define (raise-check code msg
                     #:srcloc [src #f]
                     #:agent-name [an #f]
                     #:hints [hints '()])
  (define (->srcloc v)
    (cond
      [(or (not v) (srcloc*? v)) v]
      [(syntax? v) (srcloc*-from-form v)]
      [else (srcloc*-from-form v)]))
  (define final-srcloc (->srcloc src))
  (define final-an
    (cond
      [(or (not an) (string? an)) an]
      [else (to-str an)]))
  (define prefix (format "[~a]" (symbol->string code)))
  (define msg* (if (string-prefix? msg prefix) msg (string-append prefix " " msg)))
  (raise (exn:agentlisp:check msg*
                              (current-continuation-marks)
                              code
                              final-srcloc
                              final-an
                              hints)))

;; Parse 异常（也统一 shape，这样 --json-errors 时 parser 错也能红波浪定位）
(struct exn:agentlisp:parse exn:fail
  ;; 父类型用 exn:fail（不用 exn:fail:read）：Racket 8.12 下「exn:fail:read 的子结构体 + 自有字段」
  ;; 一旦 raise 就 invalid memory reference（已用最小复现确认，与 #:transparent / guard / extra-ctor 无关）。
  ;; 自有字段命名 al-srcloc，避开与父类字段同名的歧义。
  (code al-srcloc agent-name hints)
  #:transparent
  #:extra-constructor-name make-exn:agentlisp:parse
  ;; 父 exn:fail 有 2 字段 + 自有 4 = 6 → guard 收 7 个参数（6 字段 + name）、构造器收 6 个实参。
  #:guard (lambda (msg cm code src an hints name)
            (define msg* (if (string? msg) msg (format "~a" msg)))
            (unless (symbol? code)
              (raise-argument-error 'exn:agentlisp:parse "symbol? code" code))
            (unless (or (not src) (srcloc*? src))
              (raise-argument-error 'exn:agentlisp:parse "(or/c #f srcloc*?) srcloc" src))
            (unless (or (not an) (string? an))
              (raise-argument-error 'exn:agentlisp:parse "(or/c #f string?) agent-name" an))
            (unless (and (list? hints) (andmap string? hints))
              (raise-argument-error 'exn:agentlisp:parse "(listof string?) hints" hints))
            (values msg* cm code src an hints)))

(define (raise-parse-with-srcloc code msg
                                  #:srcloc [src #f]
                                  #:agent-name [an #f]
                                  #:hints [hints '()])
  (define (->srcloc v)
    (cond
      [(or (not v) (srcloc*? v)) v]
      [(syntax? v) (srcloc*-from-form v)]
      [else (srcloc*-from-form v)]))
  (define final-srcloc (->srcloc src))
  (define final-an (if (or (not an) (string? an)) an (to-str an)))
  (define prefix (format "[~a]" (symbol->string code)))
  (define msg* (if (string-prefix? msg prefix) msg (string-append prefix " " msg)))
  (raise (exn:agentlisp:parse msg*
                              (current-continuation-marks)
                              code
                              final-srcloc
                              final-an
                              hints)))

;; ---------------- JSON Errors (SRS §5.1 / --json-errors) --------------
(define checker-default-jsexpr-version "1.0.0")

;; srcloc*? -> jsexpr（{source, line, column, position, span}，可 null）
(define (srcloc*->jsexpr s)
  (if (not s)
      (hasheq 'source #\nul 'null #f)
      (hasheq 'source   (or (srcloc*-source s)    "unknown")
              'line     (or (srcloc*-line s)      'null)
              'column   (or (srcloc*-column s)    'null)
              'position (or (srcloc*-position s)  'null)
              'span     (or (srcloc*-span s)      'null))))

(define (code->severity code-sym)
  (define s (symbol->string code-sym))
  (cond
    [(string-prefix? s "ERR_CHECK_")               "error"]
    [(string-prefix? s "ERR_KV_ALIGNMENT_")        "error"]
    [(string-prefix? s "ERR_UNGUARDED_")           "error"]
    [(string-prefix? s "ERR_CONTEXT_LEAKAGE")      "error"]
    [(string-prefix? s "PARSE_")                   "error"]
    [(string-prefix? s "WARN_")                    "warning"]
    [else                                          "error"]))

(define (code->srs-id code-sym)
  (define s (symbol->string code-sym))
  (cond
    [(string=? s "ERR_KV_ALIGNMENT_VIOLATION")    "FR-CHECK-1"]
    [(string=? s "ERR_UNGUARDED_TOOL_EXECUTION")  "FR-CHECK-2"]
    [(string=? s "ERR_CONTEXT_LEAKAGE")           "FR-CHECK-3"]
    [(string-prefix? s "ERR_CHECK_")              "FR-CHECK-0"]
    [(string-prefix? s "PARSE_")                  "FR-PARSER-0"]
    [else                                          ""]))

;; checker/parse 异常 → 统一 JSON shape
(define (exn:agentlisp:check->jsexpr e)
  (unless (exn:agentlisp:check? e)
    (raise-argument-error 'exn:agentlisp:check->jsexpr "exn:agentlisp:check?" e))
  (hasheq 'schema_version checker-default-jsexpr-version
          'code           (symbol->string (exn:agentlisp:check-code e))
          'severity       (code->severity (exn:agentlisp:check-code e))
          'srs_id         (code->srs-id (exn:agentlisp:check-code e))
          'message        (exn-message e)
          'agent_name     (or (exn:agentlisp:check-agent-name e) 'null)
          'srcloc         (srcloc*->jsexpr (exn:agentlisp:check-srcloc e))
          'hints          (exn:agentlisp:check-hints e)))

(define (exn:agentlisp:parse->jsexpr e)
  (unless (exn:agentlisp:parse? e)
    (raise-argument-error 'exn:agentlisp:parse->jsexpr "exn:agentlisp:parse?" e))
  (hasheq 'schema_version checker-default-jsexpr-version
          'code           (symbol->string (exn:agentlisp:parse-code e))
          'severity       (code->severity (exn:agentlisp:parse-code e))
          'srs_id         (code->srs-id (exn:agentlisp:parse-code e))
          'message        (exn-message e)
          'agent_name     (or (exn:agentlisp:parse-agent-name e) 'null)
          'srcloc         (srcloc*->jsexpr (exn:agentlisp:parse-al-srcloc e))
          'hints          (exn:agentlisp:parse-hints e)))

(define (exn->jsexpr e)
  "任意 Racket 异常 → JSON shape（fallback：code = RUNTIME_UNKNOWN）；
   对 exn:fail:read / exn:fail:syntax 也尽量保留 message。"
  (cond
    [(exn:agentlisp:check? e) (exn:agentlisp:check->jsexpr e)]
    [(exn:agentlisp:parse? e) (exn:agentlisp:parse->jsexpr e)]
    [else
     (define msg (if (exn? e) (exn-message e) (format "~a" e)))
     (hasheq 'schema_version checker-default-jsexpr-version
             'code           "RUNTIME_UNKNOWN"
             'severity       "error"
             'srs_id         ""
             'message        (or msg "(no message)")
             'agent_name     'null
             'srcloc         (srcloc*->jsexpr #f)
             'hints          '())]))

(define (checker-errors->jsexpr-list-thunk thunk)
  "执行 (thunk)，捕获 checker/parse 异常后返回 (values success? results-or-errors-jsexpr)。
   设计：让 main.rkt 只需要 (call-with-values (lambda () (checker-errors->jsexpr-list-thunk (lambda () (check-agent parsed)))) list)"
  (with-handlers
    ([(lambda (e) (or (exn:agentlisp:check? e) (exn:agentlisp:parse? e)))
      (lambda (e) (values #f (list (exn->jsexpr e))))]
     [exn:fail? (lambda (e) (values #f (list (exn->jsexpr e))))])
    (define v (thunk))
    (values #t v)))

;; =====================================================================
;; 主入口 (check-agent parsed)
;; 失败条件：任一项检查抛出 exn:agentlisp:check
;; 成功条件：所有检查通过，返回原 parsed（可链式传给 emitter）
;; 说明：对每个 check-* 调用，都尝试从 parsed 里抓 agent-name / 近似 srcloc（通过 raw/name）
;; =====================================================================

(define (check-agent parsed)
  (define name-val (hash-ref parsed 'name #f))
  (define name (and name-val (to-str name-val)))
  (define raw (hash-ref parsed 'raw #f))
  (define approx-srcloc (and raw (srcloc*-from-form raw)))
  (parameterize ([current-checker-source-name (current-checker-source-name)])
    (with-handlers ([exn:agentlisp:check?
                     (lambda (e)
                       ;; 如果抛错时未填 agent-name / srcloc，用外层 parsed 的近似值兜底
                       (define old-an (exn:agentlisp:check-agent-name e))
                       (define old-src (exn:agentlisp:check-srcloc e))
                       (define new-an (or old-an name))
                       (define new-src (or old-src approx-srcloc))
                       (if (and (equal? old-an new-an) (equal? old-src new-src))
                           (raise e)
                           (raise (struct-copy exn:agentlisp:check e
                                               [agent-name new-an]
                                               [srcloc new-src]))))])
      (check-kv-alignment-order   parsed)   ; SRS §4 Invariant #1
      (check-unguarded-tool-execution parsed)   ; SRS §4 Invariant #2
      (check-context-leakage      parsed)   ; SRS §4 Invariant #3
      (check-shapes               parsed)   ; 枚举值域形状（AC-1 parser boundary 断言）
      parsed)))

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
  (define name-h (to-str (hash-ref parsed 'name 'anon)))
  (define raw-h (hash-ref parsed 'raw #f))
  (define ctx-pos   (index-of order ':context))
  (define model-pos (index-of order ':model))
  (define tools-pos (index-of order ':tools))
  (when (or (and model-pos ctx-pos (> model-pos ctx-pos))
            (and tools-pos ctx-pos (> tools-pos ctx-pos)))
    (raise-check 'ERR_KV_ALIGNMENT_VIOLATION
                 (format "静态块 (:model/:tools) 出现在动态块 :context 之后（实际顺序=~a）" order)
                 #:srcloc (and raw-h (srcloc*-from-form raw-h))
                 #:agent-name name-h
                 #:hints '("SRS §4.1.1 KV 顺序必须是 :model → :tools → :context（允许缺 harness/multiagent）"
                           "把 :context 整块移动到 :tools 之后即可修复")))
  ;; P1 新增：递归检查 scoped-worker
  (define multi (hash-ref parsed 'multi #f))
  (when multi
    (for ([w (in-list (hash-ref multi 'workers '()))])
      (define w-name (to-str (hash-ref w 'name 'anon)))
      (define w-raw  (hash-ref w 'raw-blocks #f))
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
                     (format "scoped-worker=~a: 静态块出现在动态块之后（实际顺序=~a）" w-name w-order)
                     #:srcloc (and w-raw (srcloc*-from-form w-raw))
                     #:agent-name w-name
                     #:hints '("scoped-worker 的 :model/:tools 也必须在 :context 之前（SRS §4.3 FR-MAGT-1）"
                               "把该 worker 的 :context 移到 :tools 之后即可"))))))

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
  (define name (to-str (hash-ref parsed 'name 'anon)))
  (define raw  (hash-ref parsed 'raw #f))
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
                     (hash-ref verify 'reviewer_agent)))
       #:srcloc (and raw (srcloc*-from-form raw))
       #:agent-name name
       #:hints (list
                (format "工具 ~a 在 SIDEEFFECT-BUILTIN-TOOLS 内（bash / git-push / wget / curl / scp / dd / chmod / sudo 默认都是），必须有护栏" unguarded)
                "方法 A：把工具名加到 (:constrain :require-human-approval (TOOL…))，并确保 forbidden-commands 至少 1 条非空"
                "方法 B：(:verify :json-schema #t / :linter-check #t / :test-runner \"…\" / :reviewer-agent \"judge\") 任一项开启"))))

  ;; P1 新增：递归 scoped-worker 侧工具同样要受 ERR_UNGUARDED 检查（原实现仅父级）
  (define multi (hash-ref parsed 'multi #f))
  (when multi
    (for ([w (in-list (hash-ref multi 'workers '()))])
      (define w-name (to-str (hash-ref w 'name 'anon)))
      (define w-raw (hash-ref w 'raw-blocks #f))
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
                               w-name w-unguarded w-ap w-fb)
                       #:srcloc (and w-raw (srcloc*-from-form w-raw))
                       #:agent-name w-name
                       #:hints '("scoped-worker 的护栏与父级一致：require-human-approval+forbidden 双护栏 OR verify 断言"
                                 "建议：父级写 (:harness (:constrain …))，scoped-worker 显式复用同一份约束避免遗漏")))))))

;; =====================================================================
;; Invariant #3：ERR_CONTEXT_LEAKAGE
;; scoped-worker 内部的 define-tools 名必须与：
;;   (a) 父级 define-tools 完全不重名
;;   (b) 兄弟 scoped-worker 之间 define-tools 完全不重名
;; 满足任一项重名 = ERR_CONTEXT_LEAKAGE（离开作用域后 trajectory 可能误复用）
;; =====================================================================

(define (check-context-leakage parsed)
  (define name (to-str (hash-ref parsed 'name 'anon)))
  (define raw  (hash-ref parsed 'raw #f))
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
                           (cadr info) n)
                   #:srcloc (and raw (srcloc*-from-form raw))
                   #:agent-name name
                   #:hints (list
                            (format "工具 ~a 与父级 define-tools 重名（FR-CHECK-3 不变量），请重命名该 worker 工具" n)
                            "SRS §4.3：所有 scoped-worker define-tools 名必须父子/兄弟两两不重名")))
    ;; (b) 兄弟冲突
    (let ([seen #hash()])
      (for* ([w workers]
             [t (hash-ref (hash-ref w 'tools #hash()) 'define_tools '())])
        (define n (hash-ref t 'name))
        (define w-name (to-str (hash-ref w 'name 'anon)))
        (cond
          [(hash-has-key? seen n)
           (raise-check 'ERR_CONTEXT_LEAKAGE
                        (format "兄弟 scoped-worker 工具名冲突：worker=~a 与 worker=~a 均定义 ~a；可能导致 cross-worker trajectory 混淆"
                                (hash-ref seen n) w-name n)
                        #:srcloc (and raw (srcloc*-from-form raw))
                        #:agent-name w-name
                        #:hints (list
                                 (format "重名工具 ~a：请把两个 worker 的 define-tools 名改为不同（例如加前缀 w1- / w2-）" n)
                                 "SRS FR-CHECK-3：兄弟 worker 的工具名必须两两互斥（编译期就断，避免运行时轨迹泄漏）"))]
          [else (set! seen (hash-set seen n w-name))])))))

;; =====================================================================
;; Shapes / 枚举值域断言（对齐 SRS §3 EBNF 枚举表）
;; 所有不通过以 ERR_CHECK_* 开头的错误码抛出，供 AC-1 parser boundary 反例断言
;; =====================================================================

(define (check-shapes parsed)
  (define name (to-str (hash-ref parsed 'name 'anon)))
  (define raw  (hash-ref parsed 'raw #f))
  ;; (1) harness.correct.on_failure ∈ CORRECT-ON-FAILURE-ENUM
  (define on-fail (hash-ref (hash-ref (hash-ref parsed 'harness) 'correct) 'on_failure))
  (unless (enum-member? on-fail CORRECT-ON-FAILURE-ENUM)
    (raise-check 'ERR_CHECK_HARNESS_CORRECT_ON_FAILURE_ENUM
                 (format "on_failure=~a，合法值=~a（注意：spec 使用连字符 ask-human，非下划线 ask_human）"
                         on-fail CORRECT-ON-FAILURE-ENUM)
                 #:srcloc (and raw (srcloc*-from-form raw)) #:agent-name name
                 #:hints '("把下划线 ask_human / fallback_model / abort_then_rollback 改成连字符"
                           "合法值: ask-human | fallback-model | abort")))

  ;; (2) model.provider ∈ PROVIDER-ENUM
  (define provider (hash-ref (hash-ref parsed 'model) 'provider))
  (unless (enum-member? provider PROVIDER-ENUM)
    (raise-check 'ERR_CHECK_MODEL_PROVIDER_ENUM
                 (format "model.provider=~a，合法值=~a" provider PROVIDER-ENUM)
                 #:srcloc (and raw (srcloc*-from-form raw)) #:agent-name name
                 #:hints (list "provider 必须是字符串（ anthropic / openai / qwen / mock 四选一）"
                               "如果是新 provider 请先更新 checker.rkt 的 PROVIDER-ENUM 常量（枚举 SSOT）")))

  ;; (3) model.temperature ∈ [0.0, 1.0]
  (define t (hash-ref (hash-ref parsed 'model) 'temperature))
  (unless (and (real? t) (>= t 0.0) (<= t 1.0))
    (raise-check 'ERR_CHECK_MODEL_TEMPERATURE_RANGE
                 (format "model.temperature=~a，要求 0.0 ≤ t ≤ 1.0（禁止 2.0 这类非法值）" t)
                 #:srcloc (and raw (srcloc*-from-form raw)) #:agent-name name
                 #:hints '("temperature 必须是 [0.0, 1.0] 之间的实数"
                           "高创造性任务建议 0.2~0.7，代码修复建议 0.1~0.3")))

  ;; (4) context.memory-policy.layers 子集 ⊆ MEMORY-LAYER-ENUM
  (define mp (hash-ref (hash-ref parsed 'context) 'memory_policy #f))
  (when mp
    (define layers (hash-ref mp 'layers '()))
    (for ([l (in-list layers)]
          #:unless (enum-member? l MEMORY-LAYER-ENUM))
      (raise-check 'ERR_CHECK_MEMORY_LAYER_ENUM
                   (format "memory-policy.layers 非法值 ~a，合法值=~a" l MEMORY-LAYER-ENUM)
                   #:srcloc (and raw (srcloc*-from-form raw)) #:agent-name name
                   #:hints (list "记忆层枚举使用连字符格式：L0-Abstract / L1-Overview / L2-FullText（SRS §3.4）"
                                 "顺序建议按 L0→L1→L2，与 build_kv_aligned_context 的 mounted_layers 一致"))))

  ;; (5) multi.topology ∈ TOPOLOGY-ENUM
  (define multi (hash-ref parsed 'multi #f))
  (when multi
    (define top (hash-ref multi 'topology))
    (unless (enum-member? top TOPOLOGY-ENUM)
      (raise-check 'ERR_CHECK_MULTIAGENT_TOPOLOGY_ENUM
                   (format "topology=~a，合法值=~a" top TOPOLOGY-ENUM)
                   #:srcloc (and raw (srcloc*-from-form raw)) #:agent-name name
                   #:hints '("拓扑枚举使用连字符：peer / orchestration / decentralised / judge-driven"
                             "代码修复场景默认 topology=judge-driven（reviewer 打分 ≥ 0.8 才通过，τ²-bench 要求）"))))

  ;; (6) status_bar.custom 覆盖保留 key 仅 WARN（不抛）
  (define custom (hash-ref (hash-ref (hash-ref parsed 'context) 'status_bar) 'custom (hash)))
  (for ([k (in-list '("step_count" "current_branch" "test_status" "time_tracker" "todo_list"))])
    (when (hash-has-key? custom k)
      (log-warning "[WARN] status_bar.custom 覆盖保留键 ~a（可能被默认值覆盖）" k)))
  parsed)
