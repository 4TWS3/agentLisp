#lang racket/base

;; =====================================================================
;; AgentLisp Pattern Macros · 设计模式宏扩展层 MVP v1.0
;; 对应：AgentLisp 设计模式宏扩展层技术交底与实现规范 §3 / §4
;; 架构：宏展开 = 纯 S-exp 构造层（不触碰 checker.rkt/parser.rkt/emitter.rkt）
;;       → 语法展开时 已保证 5 块严格 order 输出（KV Cache 静态前缀对齐 · FR-PATTERN-02）
;;       → 由 caller（main.rkt Macro Expansion Pass，未来 C1 触碰批准后接入）
;;          执行 (syntax->datum (expand (datum->syntax #f raw-sexp)))
;;          将高层糖语法还原为 define-agent/defagent 形状后，走现有 parse-defagent 流水线
;; 枚举 Single Source of Truth：100% 从 compiler/checker.rkt 重导出，禁止自造枚举常量
;; =====================================================================

(require (for-syntax racket/base
                     racket/syntax
                     racket/string
                     racket/match)
         "checker.rkt")

(provide defreflect-agent
         defrouter-agent
         defchain-agent
         defparallel-agent
         defplanner-agent
         ;; 导出给 main.rkt Macro Expansion Pass 用的纯函数（syntax/宏双调用皆可）
         reorder-blocks
         splice-to-define-agent)

;; ---------------------------------------------------------------------
;; 枚举 SSoT 引用（compile-time / run-time 双用，用宏阶段 require checker.rkt 已保证同一份）
;; 若未来 checker.rkt 枚举变更（如 PROVIDER-ENUM 追加 "deepseek"），本模块零修改自动生效
;; ---------------------------------------------------------------------
(define-for-syntax LEGAL-PROVIDERS  (map symbol->string PROVIDER-ENUM))
(define-for-syntax LEGAL-MEM-LAYERS MEMORY-LAYER-ENUM)
(define-for-syntax LEGAL-CORRECT    CORRECT-ON-FAILURE-ENUM)
(define-for-syntax LEGAL-TOPOLOGY   TOPOLOGY-ENUM)
(define-for-syntax SIDEEFFECT-BUILTINS SIDEEFFECT-BUILTIN-TOOLS)

;; =====================================================================
;; 2 纯函数辅助（FR-PATTERN-02：反序自动提升为 :model→:tools→:context→:harness→:multiagent）
;; =====================================================================

(define (reorder-blocks blocks)
  ;; blocks 已解析为 tag 标识的 list（元素首元素为 :model/:tools/...）
  ;; 输出严格按 5 槽位排序；多同 tag 直接保留（上层 parse-defagent 会抛重复错误）
  (define order-preference
    (hasheq ':model     0
            ':tools     1
            ':context   2
            ':harness   3
            ':multiagent 4))
  (define (tag-of b)
    (define maybe-tag (and (pair? b) (car b)))
    (if (keyword? maybe-tag) maybe-tag ':unknown))
  (define (pref-of tag) (hash-ref order-preference tag 999))
  (sort (for/list ([b (in-list blocks)]) b)
        (lambda (a b)
          (< (pref-of (tag-of a)) (pref-of (tag-of b))))))

(define (splice-to-define-agent name expanded-blocks)
  ;; 与 main.rkt L176 pair? 匹配 define-agent 形状字节级全等：
  ;; (define-agent NAME BLOCK-0 BLOCK-1 ...)
  `(define-agent ,name ,@expanded-blocks))

;; =====================================================================
;; 通用编译期辅助（for-syntax）
;; =====================================================================

(begin-for-syntax

  (define (stx->keyword kw-or-datum)
    (cond
      [(keyword? kw-or-datum) kw-or-datum]
      [(symbol?  kw-or-datum) (string->keyword (symbol->string kw-or-datum))]
      [(string?  kw-or-datum) (string->keyword kw-or-datum)]
      [else (error 'stx->keyword "expected keyword-like, got: ~s" kw-or-datum)]))

  (define (extract-kws stx-kvs required optional)
    ;; kws 格式是交错的 keyword / value（类似 Racket #:kw val），但 spec 用 :kw val（单冒号非 Racket keyword）
    ;; 这里的入参已在宏 match 中被 match 到 ':provider 等 keyword-like 符号
    (define (kw<? a b)
      (string<? (keyword->string a) (keyword->string b)))
    (let loop ([kvs stx-kvs]
               [acc   (hasheq)])
      (syntax-case kvs ()
        [() acc]
        [(kw v . rest)
         (let* ([kw-sym (syntax-e #'kw)]
                [normalized (cond
                              [(keyword? kw-sym) (string->symbol (keyword->string kw-sym))]
                              [(symbol?  kw-sym) kw-sym]
                              [else (error 'extract-kws "bad keyword syntax: ~s" (syntax->datum #'kw))])])
           (loop #'rest (hash-set acc normalized (syntax->datum #'v))))]
        [_ (error 'extract-kws "bad kvs list, expected :kw val pairs, got: ~s" (syntax->datum stx-kvs))])))

  ;; 通用：工具列表在 .al 糖语法中通常是符号 (bash pytest ...)，展开时转成 import-builtin 包裹
  (define (tools->builtins tools-list)
    (for/list ([t (in-list tools-list)])
      (define t-sym (if (syntax? t) (syntax-e t) t))
      `(import-builtin ,t-sym)))

  ;; 通用：scoped-worker 单体展开模板（defrouter / defparallel 复用）
  (define (emit-scoped-worker name* provider model-name sys-prompt builtin-tools)
    `(scoped-worker ,name*
                    (:model :provider ,provider
                            :name ,model-name
                            :temperature 0.2
                            :system-prompt ,sys-prompt)
                    (:tools ,@(tools->builtins builtin-tools))
                    (:context :memory-policy (:markdown-fs (format "workers/~a.md" (quote ,name*))
                                                      :layers (L0-Abstract L1-Overview)
                                                      :auto-append #t))
                    (:harness (:constrain :forbidden-commands ("rm -rf /" "sudo rm -rf /" "chmod 777 /"))
                              (:verify  :linter-check #t)
                              (:correct :on-failure retry :max-retries 3
                                        :fallback abort)))))

;; =====================================================================
;; 宏 1/5：defreflect-agent（§4.1 L254-L280 模板 VERBATIM）
;; =====================================================================

(define-syntax (defreflect-agent stx)
  (syntax-case stx ()
    [(_ name*
        (~or (~optional (~seq :provider provider*))
             (~optional (~seq :model-name model*))
             (~optional (~seq :tools tools-list*))
             (~optional (~seq :critic critic*))
             (~optional (~seq :max-retries mx*)))
        ...
        (~or (~optional (~seq :system-prompt-override sp-override*)))
        ...
        body* ...)
     (let* ([cfg (extract-kws #'(provider* ... model* ... tools-list* ... critic* ... mx* ... sp-override* ...)
                              '(provider model-name tools critic max-retries)
                              '(system-prompt-override))]
            [provider     (hash-ref cfg 'provider     (lambda () (error 'defreflect-agent ":provider 是必需")))]
            [model-name   (hash-ref cfg 'model-name   (lambda () (error 'defreflect-agent ":model-name 是必需")))]
            [tools-list   (hash-ref cfg 'tools        (lambda () (error 'defreflect-agent ":tools (t1 t2 ...) 是必需")))]
            [critic       (hash-ref cfg 'critic       (lambda () '"审查"))]
            [max-retries  (hash-ref cfg 'max-retries  (lambda () 3))]
            [sp-override  (hash-ref cfg 'system-prompt-override #f)]
            [REFLECT-SP   (if sp-override
                              sp-override
                              (string-join
                               (list
                                "你是一个专家级代码审查 Agent，遵循 Reflection 工作流："
                                "1. 接收代码与 diff；"
                                "2. 按 CR-35 Code Review Rubric 逐类审查：语义正确性、性能/安全/可维护性；"
                                "3. 对每个问题给出具体证据（文件/行号/原文摘录）；"
                                "4. 按严重性优先级输出：Block > Critical > Major > Minor > Info；"
                                "5. 最终结论：Approve / Request Changes / Reject。")
                               "\n"))])
       (with-syntax ([provider      (datum->syntax stx provider)]
                     [model-name    (datum->syntax stx model-name)]
                     [max-retries   (datum->syntax stx max-retries)]
                     [critic        (datum->syntax stx critic)]
                     [REFLECT-SP    (datum->syntax stx REFLECT-SP)])
         #`(defagent name*
             (:model :provider provider
                     :name model-name
                     :temperature 0.2
                     :system-prompt REFLECT-SP)
             (:tools #,@(for/list ([t (in-list tools-list)])
                          #`(import-builtin #,(datum->syntax stx t)))
                     (import-mcp "http://localhost:8000/mcp"))
             (:context :memory-policy (:markdown-fs "memory/reflect.md"
                                               :layers (L0-Abstract L1-Overview)
                                               :auto-append #t)
                       :status-bar (#:id review-progress :label "审查进度"
                                            :schema (enum ("Not Started" "In Progress" "Completed" "Blocked"))
                                            :required #t)
                       :compression "L1-Overview→Summary")
             (:harness (:constrain :require-human-approval (#,@(for/list ([t tools-list]
                                                                         #:when (member t SIDEEFFECT-BUILTINS symbol=?)
                                                                         #:when (not (eq? t 'bash)))
                                                                t))
                                            :forbidden-commands ("rm -rf /" "git push --force"
                                                                   "chmod 777 /" "sudo rm -rf /"))
                       (:verify  :json-schema #t
                                 :linter-check #t
                                 :test-runner "python3 -m pytest -q"
                                 :reviewer-agent critic)
                       (:correct :on-failure retry
                                 :max-retries max-retries)))))]))

;; =====================================================================
;; 宏 2/5：defrouter-agent（§4.1 L282-L320 模板 VERBATIM）
;; =====================================================================

(define-syntax (defrouter-agent stx)
  (syntax-case stx (:routes :model)
    [(_ name*
        :model (provider* model-name*)
        :routes ([intent-kw* intent-sym* => worker-sym*] ...)
        extra-kws* ...)
     (let ([sys-prompt
            "你是一个意图识别 + 智能路由网关（Operational Gateway）："
            "1. 接收用户输入；"
            "2. 依据 (:intent ...) 路由表进行零歧义分类；"
            "3. 将任务分派到对应子 scoped-worker 执行；"
            "4. 收到子 Worker 结果后，做结果一致性摘要。"])
       (with-syntax ([sys-prompt-syn (datum->syntax stx sys-prompt)])
         #`(defagent name*
             (:model :provider provider*
                     :name model-name*
                     :temperature 0.1
                     :system-prompt sys-prompt-syn)
             (:tools (import-builtin bash))
             (:context :memory-policy (:markdown-fs "memory/router.md"
                                               :layers (L0-Abstract L1-Overview)
                                               :auto-append #t)
                       :status-bar (#:id last-intent :label "Last Intent"
                                            :schema (enum (intent-sym* ... "UNCLASSIFIED"))
                                            :required #t))
             (:harness (:constrain :forbidden-commands ("rm -rf /" "sudo rm -rf /"))
                       (:verify  :json-schema #t)
                       (:correct :on-failure retry
                                 :max-retries 2
                                 :fallback-model ("anthropic" "claude-3-7-sonnet")))
             (:multiagent
              :topology orchestration
              :workers (#,@(for/list ([w (in-list (syntax->datum #'(worker-sym* ...)))])
                            #,(emit-scoped-worker w
                                                   (syntax-e #'provider*)
                                                   (syntax-e #'model-name*)
                                                   (format "Worker ~a：执行分派后的子任务，并向网关返回结构化结果。" w)
                                                   '(bash git-push)))))))]))

;; =====================================================================
;; 宏 3/5：defchain-agent（§3 EBNF L66-L78 展开映射推导）
;; =====================================================================

(define-syntax (defchain-agent stx)
  (syntax-case stx (:steps :model :tools)
    [(_ name*
        (~or (~optional (~seq :model (provider* model-name*)))
             (~optional (~seq :steps ([prompt-s* out-sym*] ...))))
        ...
        extra-kws* ...)
     (let* ([steps-dat (syntax->datum #'((prompt-s* out-sym*) ...))]
            [n-steps    (length steps-dat)]
            [provider   (if (bound-identifier=? #'provider* #'provider*) (syntax-e #'provider*) "anthropic")]
            [model-name (if (bound-identifier=? #'model-name* #'model-name*) (syntax-e #'model-name*) "claude-3-7-sonnet")]
            [CHAIN-SP
             (string-join
              `("你是多步骤提示链执行 Agent（Prompt Chaining）："
                ,(format "总步骤数：N=~a" n-steps)
                ,@(for/list ([i (in-naturals 1)] [step steps-dat])
                     (format "Step ~a：输入 = 上一步输出 + 提示「~a」；输出变量绑定为 ~a"
                             i (car step) (cadr step)))
                "5. 保证严格按顺序执行，严禁并行或跳步。"
                "6. 若任意 Step 失败，调用 :correct retry 最多 3 次。")
              "\n")]
            [order-assertion (format "Step1 MUST before Step2，Step~a last" n-steps)])
       (with-syntax ([CHAIN-SP order-assertion (datum->syntax stx CHAIN-SP)
                                                   (datum->syntax stx order-assertion)])
         #`(defagent name*
             (:model :provider #,(datum->syntax stx provider)
                     :name #,(datum->syntax stx model-name)
                     :temperature 0.2
                     :system-prompt CHAIN-SP)
             (:tools (import-builtin bash))
             (:context :memory-policy (:markdown-fs "memory/chain.md"
                                               :layers (L0-Abstract L1-Overview)
                                               :auto-append #t)
                       :skills ("chain-prompting" "output-variable-binding"))
             (:harness (:constrain :forbidden-commands ("rm -rf /"))
                       (:verify  :linter-check #t
                                 :step-order-assertion order-assertion)
                       (:correct :on-failure retry
                                 :max-retries 3))
             (:multiagent
              :topology orchestration
              :workers (#,@(for/list ([i (in-naturals 1)] [step steps-dat])
                            (define w-name (string->symbol (format "step-~a-~a" i (cadr step))))
                            #,(emit-scoped-worker w-name provider model-name
                                                   (format "Step ~a：执行 Prompt Chaining 的第 ~a 步，提示文本：~a；输出绑定为变量 ~a"
                                                           i i (car step) (cadr step))
                                                   '(bash)))))))]))

;; =====================================================================
;; 宏 4/5：defparallel-agent（§3 EBNF L95-L106 展开映射推导）
;; =====================================================================

(define-syntax (defparallel-agent stx)
  (syntax-case stx (:branches :reducer :model)
    [(_ name*
        :branches ([branch-sym* branch-desc*] ...)
        :reducer reducer-agent-sym*
        (~or (~optional (~seq :model (provider* model-name*))))
        ...
        extra-kws* ...)
     (let* ([provider   (if (bound-identifier=? #'provider* #'provider*) (syntax-e #'provider*) "anthropic")]
            [model-name (if (bound-identifier=? #'model-name* #'model-name*) (syntax-e #'model-name*) "claude-3-7-sonnet")]
            [PARALLEL-SP
             (string-join
              `("你是并行搜索编排 Agent（Map-Reduce）："
                "1. 同时向以下并行分支分派相同查询："
                ,@(for/list ([b (syntax->list #'(branch-sym* ...))]
                             [d (syntax->list #'(branch-desc* ...))])
                    (format "  * ~a：~a" (syntax-e b) (syntax-e d)))
                ,(format "2. 所有分支完成后，调用聚合器 Reducer = ~a 做结果融合与去重"
                         (syntax-e #'reducer-agent-sym*)))
              "\n")])
       (with-syntax ([PARALLEL-SP (datum->syntax stx PARALLEL-SP)])
         #`(defagent name*
             (:model :provider #,(datum->syntax stx provider)
                     :name #,(datum->syntax stx model-name)
                     :temperature 0.2
                     :system-prompt PARALLEL-SP)
             (:tools (import-builtin bash))
             (:context :memory-policy (:markdown-fs "memory/parallel.md"
                                               :layers (L0-Abstract L1-Overview)
                                               :auto-append #t)
                       :status-bar (#:id branch-status :label "分支状态"
                                            :schema (struct ((branch-name string)
                                                             (status (enum ("Pending" "Running" "Completed" "Failed")))))
                                            :multiple #t
                                            :required #t))
             (:harness (:constrain :forbidden-commands ("rm -rf /"))
                       (:verify  :json-schema #t
                                 :parallelism-assertion "branch-a and branch-b turns may be interleaved")
                       (:correct :on-failure retry
                                 :max-retries 2))
             (:multiagent
              :topology orchestration
              :workers (#,@(for/list ([b (syntax->list #'(branch-sym* ...))]
                                       [d (syntax->list #'(branch-desc* ...))])
                             #,(emit-scoped-worker (syntax-e b)
                                                    provider
                                                    model-name
                                                    (format "并行分支 ~a 执行搜索：~a" (syntax-e b) (syntax-e d))
                                                    '(bash wget curl)))
                       #,(emit-scoped-worker (syntax-e #'reducer-agent-sym*)
                                              provider
                                              model-name
                                              (format "聚合 Reducer：收集所有并行分支结果 → 去重 → 融合 → 输出统一答案")
                                              '(bash)))))))]))

;; =====================================================================
;; 宏 5/5：defplanner-agent（§3 EBNF L108-L120 展开映射推导）
;; =====================================================================

(define-syntax (defplanner-agent stx)
  (syntax-case stx (:planner-prompt :executor-tools :model)
    [(_ name*
        :model (provider* model-name*)
        :planner-prompt planner-prompt*
        :executor-tools (exec-tool* ...)
        extra-kws* ...)
     (let* ([exec-tools-list (syntax->datum #'(exec-tool* ...))]
            [PLANNER-SP
             (string-join
              (list
               (format "你是规划执行 Agent（Planner-Executor）。初始规划提示：\n~a\n" (syntax-e #'planner-prompt*))
               "执行规则："
               "P1. 先制定总计划：plan_total ∈ [3, 5]（3~5 步，防止过长/过短）；"
               "P2. 逐步执行 P1..Pn..FIN 链：每一步 (a) 生成子任务描述 → (b) 仅允许使用 executor-tools 列表中的工具执行 → (c) 写入 L0/L1 Markdown 记忆层；"
               "P3. 最终检查：plan_done == plan_total，且 FIN 步骤 unfinished = []。"
               (format "Executor 工具白名单：~a（调用其它工具一律视为越权行为，被 harness :constrain 直接拦截）" exec-tools-list))
              "\n")]
            [plan-count-assertion "plan_total ∈ [3, 5]；FIN unfinished=[]"])
       (with-syntax ([PLANNER-SP plan-count-assertion
                                      (datum->syntax stx PLANNER-SP)
                                      (datum->syntax stx plan-count-assertion)])
         #`(defagent name*
             (:model :provider provider*
                     :name model-name*
                     :temperature 0.0
                     :system-prompt PLANNER-SP)
             (:tools #,@(for/list ([t exec-tools-list])
                          #`(import-builtin #,(datum->syntax stx t))))
             (:context :memory-policy (:markdown-fs "memory/planner.md"
                                               :layers (L0-Abstract L1-Overview L2-FullText)
                                               :auto-append #t)
                       :skills ("deep-research-plan" "cross-source-verification")
                       :status-bar (#:id plan-tracker :label "Planner Plan"
                                            :schema (struct ((step-index integer)
                                                             (step-desc string)
                                                             (status (enum ("Todo" "Doing" "Done"))))
                                            :multiple #t
                                            :todo-list #t
                                            :required #t))
             (:harness (:constrain :require-human-approval (#,@(for/list ([t exec-tools-list]
                                                                         #:when (member t SIDEEFFECT-BUILTINS symbol=?)
                                                                         #:when (not (memq t '(bash))))
                                                                t))
                                            :forbidden-commands ("rm -rf /" "git push --force")
                                            :max-concurrent-turns 4)
                       (:verify  :json-schema #t
                                 :plan-completion-assertion plan-count-assertion)
                       (:correct :on-failure retry
                                 :max-retries 3
                                 :fallback abort)))))]))

;; =====================================================================
;; info.rkt 集合 registration（供 raco setup 把本模块识别为 agentlisp/compiler/patterns）
;; =====================================================================
(module+ test)
