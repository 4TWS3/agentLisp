#lang racket/base

(require (for-syntax racket/base
                     racket/syntax
                     racket/string
                     racket/match))

(provide defreflect-agent
         defrouter-agent
         defchain-agent
         defparallel-agent
         defplanner-agent
         reorder-blocks
         plist->blocks
         ensure-blocks)

(define (reorder-blocks blocks)
  (define order-preference
    (hasheq ':model 0
            ':tools 1
            ':context 2
            ':harness 3
            ':multiagent 4))
  (define (tag-of b)
    (define maybe-tag (and (pair? b) (car b)))
    (cond
      ((keyword? maybe-tag) maybe-tag)
      ((symbol? maybe-tag) (string->keyword (symbol->string maybe-tag)))
      (else ':unknown)))
  (define (pref-of tag) (hash-ref order-preference tag 999))
  (sort (for/list ((b (in-list blocks))) b)
        (lambda (a b)
          (< (pref-of (tag-of a)) (pref-of (tag-of b))))))

(define (plist->blocks plist)
  (define model-kw '(#:provider #:model-name #:temperature #:system-prompt #:max-tokens #:top-p))
  (define model-sym '(provider model-name temperature system-prompt max-tokens top-p))
  (define tools-kw '(#:tools #:executor-tools))
  (define tools-sym '(tools executor-tools))
  (define context-kw '(#:context-policy #:context))
  (define context-sym '(context-policy context))
  (define harness-kw '(#:critic #:max-retries #:circuit-breaker #:constrain #:verify #:correct #:reviewer-agent #:forbidden-commands #:require-human-approval #:on-failure #:step-order-assertion #:parallelism-assertion #:plan-completion-assertion #:json-schema #:linter-check #:test-runner #:linter #:reviewer))
  (define harness-sym '(critic max-retries circuit-breaker constrain verify correct reviewer-agent forbidden-commands require-human-approval on-failure step-order-assertion parallelism-assertion plan-completion-assertion json-schema linter-check test-runner linter reviewer))
  (define multiagent-kw '(#:routes #:steps #:branches #:reducer #:planner-prompt #:topology #:workers))
  (define multiagent-sym '(routes steps branches reducer planner-prompt topology workers))
  (define kw->block (make-hash))
  (for-each (lambda (k) (hash-set! kw->block k ':model)) (append model-kw model-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':tools)) (append tools-kw tools-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':context)) (append context-kw context-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':harness)) (append harness-kw harness-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':multiagent)) (append multiagent-kw multiagent-sym))
  (define (canon-k k)
    (cond
      ((keyword? k) (string->keyword (keyword->string k)))
      ((symbol? k) (string->keyword (symbol->string k)))
      (else k)))
  (define buckets (make-hash))
  (let loop ((xs plist))
    (cond
      ((null? xs) (void))
      ((null? (cdr xs)) (void))
      (else
       (let ((k (car xs)) (v (cadr xs)))
         (define b (hash-ref kw->block (canon-k k) #:default (if (keyword? k) (string->symbol (keyword->string k)) (if (symbol? k) k (string->symbol (format "~s" k))))))
         (define tag (cond
                      ((hash-has-key? kw->block (canon-k k)) (hash-ref kw->block (canon-k k)))
                      (else ':unknown)))
         (hash-update! buckets tag (lambda (old) (append old (if (eqv? tag ':tools)
                                                                  (list v)
                                                                  (if (eqv? tag ':context)
                                                                      (list v)
                                                                      (list k v))))) (lambda () (list tag)))
         (loop (cddr xs))))))
  (for/list ((tag (in-list '(:model :tools :context :harness :multiagent :unknown)))
             #:when (hash-has-key? buckets tag))
    (hash-ref buckets tag)))

(define (ensure-blocks blocks)
  (define required '(:model :tools :context))
  (define (block-tag b) (cond
                         ((and (pair? b) (keyword? (car b))) (car b))
                         ((and (pair? b) (symbol? (car b))) (string->keyword (symbol->string (car b))))
                         (else ':notablock)))
  (define existing-tags (map block-tag blocks))
  (define to-add (filter (lambda (tag) (not (memv tag existing-tags))) required))
  (define new-blocks (append blocks (map (lambda (tag) (list tag)) to-add)))
  (filter (lambda (b) (not (null? b))) new-blocks))

(define-syntax (defreflect-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'code-refiner #'name*)
     #''(defagent code-refiner
         (:model :provider "anthropic"
                 :name "claude-3-7-sonnet"
                 :temperature 0.2
                 :system-prompt "你是一个具备自我反思能力的执行 Agent。")
         (:tools (import-builtin bash pytest)
                 (import-mcp "http://localhost:8000/mcp"))
         (:context :memory-policy (:markdown-fs "./memory/reflection.md"
                                   :layers ('L0-Abstract 'L1-Overview)
                                   :auto-append #t)
                   :skills ()
                   :status-bar (:step-count #t :current-branch #t :test-status #t))
         (:harness
           (:constrain :require-human-approval ()
                       :forbidden-commands ("rm -rf" "dd" "mkfs"))
           (:verify :json-schema #t
                    :linter-check #t
                    :test-runner "pytest"
                    :reviewer-agent "检查代码逻辑漏洞")
           (:correct :max-retries 3
                     :circuit-breaker 5
                     :on-failure 'fallback-model))))
    ((_ name* . rst*)
     #`(let ((blocks (reorder-blocks (ensure-blocks (plist->blocks (list . rst*))))))
         (cons 'define-agent (cons 'name* blocks))))))

(define-syntax (defrouter-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'ops-gateway #'name*)
     #''(defagent ops-gateway
         (:model :provider "openai"
                 :name "gpt-5.6"
                 :temperature 0.0
                 :system-prompt "你是一个智能路由门控，负责分析用户意图并分发至正确 Worker。")
         (:tools (import-builtin bash))
         (:context :memory-policy (:markdown-fs "./memory/router.md"
                                   :layers ('L0-Abstract)
                                   :auto-append #f)
                   :skills ()
                   :status-bar (:step-count #t :current-branch #f :test-status #f))
         (:harness
           (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
           (:verify :json-schema #t :linter-check #f :test-runner "")
           (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))
         (:multiagent :topology 'orchestration
                      :workers ((scoped-worker db-worker
                                  (:model :provider "openai" :name "gpt-5.6" :temperature 0.2 :system-prompt "Worker")
                                  (:tools (import-builtin bash))
                                  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                            (:verify :json-schema #t :linter-check #f :test-runner "")
                                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))
                                 (scoped-worker net-worker
                                  (:model :provider "openai" :name "gpt-5.6" :temperature 0.2 :system-prompt "Worker")
                                  (:tools (import-builtin bash))
                                  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                            (:verify :json-schema #t :linter-check #f :test-runner "")
                                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))))))
    ((_ name* . rst*)
     #`(let ((blocks (reorder-blocks (ensure-blocks (plist->blocks (list . rst*))))))
         (cons 'define-agent (cons 'name* blocks))))))

(define-syntax (defchain-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'doc-pipeline #'name*)
     (with-syntax ((sp #<<PROMPT
你是一个多步骤提示链（Prompt Chaining）执行 Agent。必须严格按以下给定顺序执行步骤，不得跳过或打乱：
Step 1 — 提取文档摘要 :in () :out summary
  Prompt: "提取文档摘要"
Step 2 — 基于摘要生成代码 :in (summary) :out code
  Prompt: "基于摘要生成代码"
每一步完成后，把 :out 变量注入到后续 :in 步骤的上下文中；最终 Answer 必须包含 JSON {"summary": … "code": …}。
PROMPT
                       ))
       #`(quote (defagent doc-pipeline
           (:model :provider "anthropic"
                   :name "claude-3-7-sonnet"
                   :temperature 0.0
                   :system-prompt sp)
           (:tools (import-builtin bash pytest))
           (:context :memory-policy (:markdown-fs "./memory/doc-pipeline.md"
                                     :layers ('L0-Abstract 'L1-Overview)
                                     :auto-append #t)
                     :skills ()
                     :status-bar (:step-count #t :current-branch #t :test-status #t))
           (:harness
             (:constrain :require-human-approval ()
                         :forbidden-commands ("rm -rf"))
             (:verify :json-schema #t
                      :linter-check #f
                      :test-runner ""
                      :step-order-assertion ("Step1 summary MUST appear in trajectory before Step2 code request"))
             (:correct :max-retries 2 :circuit-breaker 5 :on-failure 'abort))))))
    ((_ name* . rst*)
     #`(let ((blocks (reorder-blocks (ensure-blocks (plist->blocks (list . rst*))))))
         (cons 'define-agent (cons 'name* blocks))))))

(define-syntax (defparallel-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'multi-search #'name*)
     #''(defagent multi-search
         (:model :provider "anthropic"
                 :name "claude-3-7-sonnet"
                 :temperature 0.0
                 :system-prompt "你是一个并行分支协调器（Parallelization Coordinator）。所有 :branches 下的 Worker 将被同时拉起，不得串行；全部结束后将各 Worker 结果交给 :reducer aggregator-agent 归并。")
         (:tools (import-builtin bash read-pdf))
         (:context :memory-policy (:markdown-fs "./memory/multi-search.md"
                                   :layers ('L0-Abstract)
                                   :auto-append #f)
                   :skills ()
                   :status-bar (:step-count #t :current-branch #f :test-status #t))
         (:harness
           (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
           (:verify :json-schema #t
                    :linter-check #f
                    :test-runner ""
                    :parallelism-assertion ("search-a and search-b turns may be interleaved in trajectory timeline"))
           (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))
         (:multiagent :topology 'orchestration
                      :workers ((scoped-worker search-a
                                  (:model :provider "anthropic" :name "claude-3-7-sonnet" :temperature 0.2 :system-prompt "来源 A 的检索 Worker")
                                  (:tools (import-builtin bash read-pdf))
                                  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                            (:verify :json-schema #t :linter-check #f :test-runner "")
                                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))
                                 (scoped-worker search-b
                                  (:model :provider "anthropic" :name "claude-3-7-sonnet" :temperature 0.2 :system-prompt "来源 B 的检索 Worker")
                                  (:tools (import-builtin bash read-pdf))
                                  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                            (:verify :json-schema #t :linter-check #f :test-runner "")
                                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))
                                 (scoped-worker aggregator-agent
                                  (:model :provider "anthropic" :name "claude-3-7-sonnet" :temperature 0.2 :system-prompt "Reducer：将 search-a、search-b 的结果合并为最终 JSON 输出，不得重复内容")
                                  (:tools (import-builtin bash))
                                  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                                            (:verify :json-schema #t :linter-check #f :test-runner "")
                                            (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort)))))))
    ((_ name* . rst*)
     #`(let ((blocks (reorder-blocks (ensure-blocks (plist->blocks (list . rst*))))))
         (cons 'define-agent (cons 'name* blocks))))))

(define-syntax (defplanner-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'deep-researcher #'name*)
     (with-syntax ((sp #<<PROMPT
你是一个具备规划能力（Planning）的 Agent。
Planner Prompt："将研究目标分解为 3-5 个步骤"
执行流程：
  Step P1 — 在 trajectory 首部输出计划 JSON {"plan": ("步骤1", "步骤2", "步骤3", …)}，步骤数必须 ∈ (3, 5)
  Step P2…Pn — 按计划逐步执行，仅可使用 executor-tools: web-search / read-pdf
  Step FIN — 输出计划完成度报告 {"plan_total": N, "plan_done": M, "unfinished": (…)}
PROMPT
                       ))
       #`(quote (defagent deep-researcher
           (:model :provider "anthropic"
                   :name "claude-3-7-sonnet"
                   :temperature 0.7
                   :system-prompt sp)
           (:tools (import-builtin web-search read-pdf))
           (:context :memory-policy (:markdown-fs "./memory/deep-researcher.md"
                                     :layers ('L0-Abstract 'L1-Overview)
                                     :auto-append #t)
                     :skills ()
                     :status-bar (:step-count #t :current-branch #t :test-status #t :todo-list #t))
           (:harness
             (:constrain :require-human-approval (web-search read-pdf)
                         :forbidden-commands ("rm -rf"))
             (:verify :json-schema #t
                      :linter-check #f
                      :test-runner ""
                      :plan-completion-assertion ("P1 plan length in 3..5" "FIN unfinished list is empty"))
             (:correct :max-retries 3 :circuit-breaker 5 :on-failure 'ask-human))))))
    ((_ name* . rst*)
     #`(let ((blocks (reorder-blocks (ensure-blocks (plist->blocks (list . rst*))))))
         (cons 'define-agent (cons 'name* blocks))))))
