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
         json
         ;; 关注点分离：parser/checker/emitter 三段式，checker 独立模块，枚举常量 Single Source of Truth
         "checker.rkt")

(provide compile-agent-lisp
         ;; 也开放给 CI / checker.rkt 复用：
         parse-defagent
         check-agent
         agent->py
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
(define (py-bool v) (if (->racket-bool v) "True" "False"))
(define (symbol<?/string a b) (string<? (to-str a) (to-str b)))

;; =====================================================================
;; 1. PARSER  修复 CRIT-1 / MAJOR-5 / MAJOR-7 / MAJOR-8 / MAJOR-9
;;   §3.4 枚举值域由 checker.rkt 常量 Single Source of Truth（parser 侧引用同一常量保证一致）
;; =====================================================================

;; defagent name Model Context Tools Harness [MultiAgent]
(define (parse-defagent form)
  (match form
    [`(defagent ,name ,blocks ...)
     (let-values ([(model ctx tools harness multi) (partition-blocks blocks name)])
       (unless model   (raise-parse `(defagent ,name) "缺少必需的 :model 块"))
       (unless ctx     (raise-parse `(defagent ,name) "缺少必需的 :context 块"))
       (unless tools   (raise-parse `(defagent ,name) "缺少必需的 :tools 块"))
       (unless harness (raise-parse `(defagent ,name) "缺少必需的 :harness 块"))
       ;; 重新获得 order：partition-blocks 之前已经算过，但这里再算一次以便落盘（保持简单，不重构多返回）
       (let-values ([(_1 _2 _3 _4 _5 order) (partition-blocks blocks name)])
         (hash 'name name
               'model   (parse-model model)
               'context (parse-context ctx)
               'tools   (parse-tools tools)
               'harness (parse-harness harness)
               'multi   (and multi (parse-multi multi))
               'order   order
               'raw form))))]
    [_ (raise-parse 'parse-defagent (format "顶层必须是 (defagent NAME BLOCK…)，得到：~s" form))]))

(define (partition-blocks blocks agent-name)
  (let loop ([bs blocks] [model #f] [ctx #f] [tools #f] [harness #f] [multi #f] [order '()])
    (if (null? bs)
        (values model ctx tools harness multi (reverse order))
        (let ([b (car bs)] [rest (cdr bs)])
          (define tag (and (pair? b) (car b)))
          (cond
            [(eq? tag ':model)   (when model (raise-parse `(defagent ,agent-name) ":model 块重复"))
                                 (loop rest b ctx tools harness multi (cons ':model order))]
            [(eq? tag ':context) (when ctx (raise-parse `(defagent ,agent-name) ":context 块重复"))
                                 (loop rest model b tools harness multi (cons ':context order))]
            [(eq? tag ':tools)   (when tools (raise-parse `(defagent ,agent-name) ":tools 块重复"))
                                 (loop rest model ctx b harness multi (cons ':tools order))]
            [(eq? tag ':harness) (when harness (raise-parse `(defagent ,agent-name) ":harness 块重复"))
                                 (loop rest model ctx tools b multi (cons ':harness order))]
            [(eq? tag ':multiagent) (when multi (raise-parse `(defagent ,agent-name) ":multiagent 块重复"))
                                     (loop rest model ctx tools harness b (cons ':multiagent order))]
            [else (raise-parse `(defagent ,agent-name)
                                (format "未知块 ~s；应为 :model/:context/:tools/:harness (可选 :multiagent)" tag))])))))

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
     (for ([l (in-list layers)])
       (unless (enum-member? l MEMORY-LAYER-ENUM)
         (raise-parse ':memory-policy (format "layer 枚举=~a，得到 ~a" MEMORY-LAYER-ENUM l))))
     (hash 'path path 'layers (map to-str layers)
           'auto_append_episodic (->racket-bool append?)  ; Python key：下划线
           'auto_append_spec_key :auto-append)]            ; 原始 spec key 留痕
    [_ (raise-parse ':memory-policy
                    (format "必需是 (:markdown-fs PATH :layers (…) :auto-append #t/#f)，得到 ~s" mp))]))

(define (parse-status-bar sb)
  (if (not sb)
      (hash 'step_count #t 'current_branch #f 'test_status #f
            'time_tracker #f 'todo_list #f 'custom (hash))
      (match sb
        [`(:status-bar . ,kvs)
         (let ([kw (keyword-kvs kvs '(:step-count :current-branch :test-status
                                               :time-tracker :todo-list))])
           (hash 'step_count    (->racket-bool (hash-ref kw ':step-count #t))
                 'current_branch(->racket-bool (hash-ref kw ':current-branch #f))
                 'test_status   (->racket-bool (hash-ref kw ':test-status #f))
                 'time_tracker  (->racket-bool (hash-ref kw ':time-tracker #f))
                 'todo_list     (->racket-bool (hash-ref kw ':todo-list #f))
                 'custom (for/hash ([(k v) (in-hash (hash-remove-keys kw '(:step-count :current-branch
                                                                              :test-status :time-tracker :todo-list)))])
                           (values (to-str k) v))))]
        [_ (raise-parse ':status-bar (format "必需是 (:status-bar …)，得到 ~s" sb))])))

;;; ---------- parse-tools (修复 MAJOR-5：支持 4 种组合：仅 builtin / 仅 mcp / 仅 define-tool / 任意组合) ----------
(define (parse-tools form)
  (match form
    [`(:tools . ,clauses)
     (let loop ([cs clauses] [builtins '()] [mcps '()] [define-tools '()])
       (if (null? cs)
           (when (and (null? builtins) (null? mcps) (null? define-tools))
             (raise-parse ':tools "至少要有一种工具源（import-builtin / import-mcp / define-tool）"))
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
             [_ (raise-parse ':tools (format "未知 tools 子句：~s" (car cs)))])))
     (hash 'builtins builtins 'mcp_servers mcps 'define_tools define-tools)]
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
       (define on-fail (hash-ref kw ':on-failure 'ask-human))
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
     (unless (enum-member? topology TOPOLOGY-ENUM)
       (raise-parse ':multiagent (format ":topology 枚举=~a，得到 ~a" TOPOLOGY-ENUM topology)))
     (hash 'topology (to-str topology)
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
(define (keyword-kvs kvs allowed)
  (let loop ([xs kvs] [out (hash)])
    (cond
      [(null? xs) out]
      [(or (null? (cdr xs)) (not (keyword? (car xs))))
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

(define (agent->py parsed)
  (define name (to-str (hash-ref parsed 'name)))
  (define cls-name (string-append (pascal-case name) "Harness"))
  (define model (hash-ref parsed 'model))
  (define ctx (hash-ref parsed 'context))
  (define tools (hash-ref parsed 'tools))
  (define harness (hash-ref parsed 'harness))
  (define multi (hash-ref parsed 'multi #f))
  (string-append
   (emit-header cls-name name)
   (emit-model-dict model)
   (emit-context-dict ctx)
   (emit-tools-config tools)
   (emit-harness-dict harness)
   (emit-multi-class-vars multi)
   (emit-init-footer cls-name)
   (emit-build-kv-aligned-context-hook)
   (emit-constrain-method harness)
   (emit-run-react-loop-stub)
   (emit-harness-registry cls-name name)))

(define (emit-header cls-name agent-name)
  (string-append
   "# -*- coding: utf-8 -*-\n"
   "# Generated by Racket AgentLisp Compiler (spec v2.0 对齐)\n"
   "# Formula: Agent = Model + Harness\n\n"
   "from __future__ import annotations\n\n"
   "from typing import Any, Dict, List, Optional\n"
   "from runtime.base_harness_v2 import BaseHarnessV2, build_kv_aligned_context\n\n"
   (format "class ~a(BaseHarnessV2):\n" cls-name)
   (format "    agent_name = ~s\n" agent-name)
   (format "    AGENT_NAME = ~s\n\n" agent-name)
   "    def __init__(self, *args: Any, **kwargs: Any) -> None:\n"
   "        # 组装 spec 规定的四个一等 dict，传给 BaseHarnessV2 四参 constructor\n"
   ))

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
          defs-dump
          agent-name))

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
  ;; 修复 CRIT-2：Status Bar 必须 system 角色；同时注入 tools_schema 静态段（修复 MINOR-14）
  ;; 注意：BaseHarnessV2.build_context() 方法签名为无参 self 版本，此处我们 override 为"接受或不接受 trajectory 参数均可"的兼容形态
  #<<EOS
    def build_context(self, trajectory=None):
        import copy as _copy
        if trajectory is None:
            trajectory = self.trajectory
        tools_openai_schema = None
        if self.tool_registry is not None:
            try:
                tools_openai_schema = self.tool_registry.to_openai_schema()
            except Exception:  # noqa: BLE001
                tools_openai_schema = None
        return build_kv_aligned_context(
            system_prompt=self.model_config.get('system_prompt', ''),
            tools_schema_text=self.tools_config.get('tools_schema'),
            tools_openai_schema=tools_openai_schema,
            trajectory=list(_copy.deepcopy(trajectory) if False else trajectory),
            step_count=self.step_count,
            status_bar_config=self.context_config.get('status_bar', {}) or {},
            terminated=self.is_terminated,
        )

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
                 (:correct :max-retries 3 :circuit-breaker 5 :on-failure ask-human)))))

  (displayln (compile-agent-lisp sample-agent-lisp)))
