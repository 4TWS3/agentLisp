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
         ;; CR-42 后续：核心语法糖宏（记忆管理 / 多智能体协作）
         defmemory-agent
         defmultiagent
         reorder-blocks
         plist->blocks
         ensure-blocks)

(begin-for-syntax
  ;; CR-42 P-3：编译期版本（GENERIC 分支在 phase 1 运行，必须定义在 begin-for-syntax 内）
  ;; US-27：加 :params——把用户 plist 里本 kind 声明过的键交给编译期提升进 :config。
  (define (append-pattern/ct blocks kind markers params)
    (append blocks
            (list (list ':pattern ':kind kind
                        ':config (list ':markers markers)
                        ':params params))))

  ;; US-27：只取 keys（冒号去掉后的符号）命中的键值对，保持输入顺序。
  (define (plist-filter/ct rst keys)
    (define (k->sym k)
      (cond ((keyword? k) (string->symbol (regexp-replace #rx"^:" (keyword->string k) "")))
            ((symbol? k) (string->symbol (regexp-replace #rx"^:" (symbol->string k) "")))
            (else #f)))
    (let loop ((xs rst) (out '()))
      (cond
        ((or (null? xs) (null? (cdr xs))) out)
        (else
         (define k (car xs))
         (define s (k->sym k))
         (loop (cddr xs)
               (if (and s (memq s keys)) (append out (list k (cadr xs))) out))))))

  (define (reorder-blocks/ct blocks)
    (define order-preference
      (hasheq ':model 0
              ':tools 1
              ':context 2
              ':harness 3
              ':multiagent 4))
    ;; US-27：剥前导冒号，返回符号，与 order-preference 的 :model 对齐。
    (define (tag-of b)
      (define t (and (pair? b) (car b)))
      (cond
        ((keyword? t) (string->symbol (string-append ":" (keyword->string t))))
        ((symbol? t) (string->symbol (if (regexp-match? #rx"^:" (symbol->string t)) (symbol->string t) (string-append ":" (symbol->string t)))))
        (else ':unknown)))
    (define (pref-of tag) (hash-ref order-preference tag 999))
    (sort (for/list ((b (in-list blocks))) b)
          (lambda (a b)
            (< (pref-of (tag-of a)) (pref-of (tag-of b))))))

  (define (plist->blocks/ct plist)
    (define model-kw '(#:provider #:model-name #:temperature #:system-prompt #:max-tokens #:top-p))
    (define model-sym '(provider model-name temperature system-prompt max-tokens top-p model))
    (define model-kw2 (cons '#:model model-kw))
    (define tools-kw '(#:tools #:executor-tools))
    (define tools-sym '(tools executor-tools))
    (define context-kw '(#:context-policy #:context))
    (define context-sym '(context-policy context))
    (define harness-kw '(#:critic #:max-retries #:circuit-breaker #:constrain #:verify #:correct #:reviewer-agent #:forbidden-commands #:require-human-approval #:on-failure #:step-order-assertion #:parallelism-assertion #:plan-completion-assertion #:json-schema #:linter-check #:test-runner #:linter #:reviewer))
    (define harness-sym '(critic max-retries circuit-breaker constrain verify correct reviewer-agent forbidden-commands require-human-approval on-failure step-order-assertion parallelism-assertion plan-completion-assertion json-schema linter-check test-runner linter reviewer harness))
    (define harness-kw2 (cons '#:harness harness-kw))
    (define multiagent-kw '(#:routes #:steps #:branches #:reducer #:planner-prompt #:topology #:workers))
    (define multiagent-sym '(routes steps branches reducer planner-prompt topology workers multiagent))
    (define multiagent-kw2 (cons '#:multiagent multiagent-kw))
    (define kw->block (make-hash))
    (for-each (lambda (k) (hash-set! kw->block k ':model)) (append model-kw2 model-sym))
    (for-each (lambda (k) (hash-set! kw->block k ':tools)) (append tools-kw tools-sym))
    (for-each (lambda (k) (hash-set! kw->block k ':context)) (append context-kw context-sym))
    (for-each (lambda (k) (hash-set! kw->block k ':harness)) (append harness-kw2 harness-sym))
    (for-each (lambda (k) (hash-set! kw->block k ':multiagent)) (append multiagent-kw2 multiagent-sym))
    ;; US-27：剥前导冒号。用户的 .al 里键写作 :routes，若不剥会得到 #::routes，
    ;; 与 kw->block 的 #:routes 不匹配 -> 整块落 :unknown -> 编译期 PARSE_GENERIC 报错。
    (define (canon-k k)
      (define s (cond ((keyword? k) (keyword->string k))
                      ((symbol? k) (symbol->string k))
                      (else (format "~a" k))))
      (string->keyword (if (regexp-match? #rx"^:" s) (substring s 1) s)))
    (define buckets (make-hash))
    ;; B-06：块头键（:tools/:harness/:context/...）+ 列表值 = 整块内容。
    ;; 不这样处理会产出 (:tools :tools (import-builtin bash))，下游看到重复键。
    (define block-heads '(#:model #:tools #:context #:harness #:multiagent))
    ;; B-06：这些键由 append-pattern 收进 (:pattern :params ...)，不进块。
    (define pattern-keys '(#:routes #:steps #:branches #:reducer #:planner-prompt))
    (define (block-items ck v)
    ;; B-06：块头键的值怎么摊进块，按块形状定：
    ;;   :tools      一个 clause        -> (tag v)
    ;;   :harness    clause 列表        -> (tag . v)
    ;;   :context    plist（:k v ...）  -> (tag . v)
    (cond
      [(eq? ck '#:tools) (list v)]
      [(eq? ck '#:harness) (if (and (list? v) (pair? v) (list? (car v))) v (list v))]
      [(eq? ck '#:context) (if (and (list? v) (pair? v) (keyword? (car v))) v (list v))]
      [(list? v) v]
      [else (list v)]))
    (define (add! tag items)
      (hash-update! buckets tag (lambda (old) (append old items)) (lambda () (list tag))))
    (let loop ((xs plist))
      (cond
        ((null? xs) (void))
        ((null? (cdr xs)) (void))
        (else
         (let* ((k (car xs)) (v (cadr xs)) (ck (canon-k k)))
           (define tag (cond
                        ((hash-has-key? kw->block ck) (hash-ref kw->block ck))
                        (else ':unknown)))
           (cond
             ((memv ck pattern-keys) (void))
             ((and (memv ck block-heads) (list? v)) (add! tag (block-items ck v)))
             ;; B-06：:model-name 下游只认 :name。
             (else (add! tag (if (eq? ck '#:model-name) (list ':name v) (list k v)))))
           (loop (cddr xs))))))
    (for/list ((tag (in-list '(:model :tools :context :harness :multiagent :unknown)))
               #:when (hash-has-key? buckets tag))
      (hash-ref buckets tag)))

  (define (ensure-blocks/ct blocks)
    ;; US-27：标签统一成符号。plist->blocks 产出的块标签是符号 :model。
    ;; 旧 block-tag 把它转成 #::model，与 required 的 :model 永不相等 -> 加空块 -> 块重复。
    ;; B-06：:harness 也是必需块（缺了 PARSE_GENERIC 直接失败）。
    (define required '(:model :tools :context :harness))
    (define (block-tag b)
      (define t (and (pair? b) (car b)))
      (cond ((keyword? t) (string->symbol (string-append ":" (keyword->string t))))
            ((symbol? t) (string->symbol (if (regexp-match? #rx"^:" (symbol->string t)) (symbol->string t) (string-append ":" (symbol->string t)))))
            (else ':notablock)))
    (define existing-tags (map block-tag blocks))
    (define to-add (filter (lambda (tag) (not (memv tag existing-tags))) required))
    ;; B-06：缺块时给可用默认，不给空块（空块会让 PARSE_GENERIC 报「缺必需 :provider」）。
    ;; 默认值与 HC 分支一致，用户显式给了就用用户的。
    (define (default-block tag)
      (cond
        [(eq? tag ':model)
         '(:model :provider "openai" :name "gpt-5.6" :temperature 0.0
                  :system-prompt "通用的任务执行 Agent。")]
        [(eq? tag ':tools) '(:tools (import-builtin bash))]
        [(eq? tag ':harness)
         '(:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                    (:verify :json-schema #t :linter-check #f :test-runner "")
                    (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))]
        [(eq? tag ':context)
         '(:context :memory-policy (:markdown-fs "./memory/default.md"
                                    :layers (L0-Abstract) :auto-append #f))]
        [else (list tag)]))
    (define (ensure-model b)
      ;; B-06：用户只写 :model-name 时也要有 provider（下游必需）。
      (if (eq? (block-tag b) ':model)
          (let* ([b1 (if (memv ':provider b) b (append b (list ':provider "openai")))]
                 [b2 (if (memv ':name b1) b1 (append b1 (list ':name "gpt-5.6")))])
            (if (memv ':system-prompt b2) b2 (append b2 (list ':system-prompt "通用的任务执行 Agent。"))))
          b))
    (define (ensure-context b)
      (if (and (eq? (block-tag b) ':context) (not (memv ':memory-policy b)))
          (append b (list ':memory-policy
                          '(:markdown-fs "./memory/default.md"
                            :layers (L0-Abstract) :auto-append #f)))
          b))
    (define new-blocks (append blocks (map default-block to-add)))
    (filter (lambda (b) (not (null? b))) (map ensure-context (map ensure-model new-blocks)))))

;; CR-42 P-3：给块列表追加 (:pattern :kind K :config (:markers (...)))。
;; US-27：加 :params（与 /ct 版同形）。
(define (append-pattern blocks kind markers params)
  (append blocks
          (list (list ':pattern ':kind kind
                      ':config (list ':markers markers)
                      ':params params))))

(define (reorder-blocks blocks)
  (define order-preference
    (hasheq ':model 0
            ':tools 1
            ':context 2
            ':harness 3
            ':multiagent 4))
  ;; US-27：剥前导冒号，返回符号（与 /ct 版同因）。
  (define (tag-of b)
    (define t (and (pair? b) (car b)))
    (cond
      ((keyword? t) (string->symbol (string-append ":" (keyword->string t))))
      ((symbol? t) (string->symbol (if (regexp-match? #rx"^:" (symbol->string t)) (symbol->string t) (string-append ":" (symbol->string t)))))
      (else ':unknown)))
  (define (pref-of tag) (hash-ref order-preference tag 999))
  (sort (for/list ((b (in-list blocks))) b)
        (lambda (a b)
          (< (pref-of (tag-of a)) (pref-of (tag-of b))))))

(define (plist->blocks plist)
  (define model-kw '(#:provider #:model-name #:temperature #:system-prompt #:max-tokens #:top-p))
  (define model-sym '(provider model-name temperature system-prompt max-tokens top-p model))
  (define model-kw2 (cons '#:model model-kw))
  (define tools-kw '(#:tools #:executor-tools))
  (define tools-sym '(tools executor-tools))
  (define context-kw '(#:context-policy #:context))
  (define context-sym '(context-policy context))
  (define harness-kw '(#:critic #:max-retries #:circuit-breaker #:constrain #:verify #:correct #:reviewer-agent #:forbidden-commands #:require-human-approval #:on-failure #:step-order-assertion #:parallelism-assertion #:plan-completion-assertion #:json-schema #:linter-check #:test-runner #:linter #:reviewer))
  (define harness-sym '(critic max-retries circuit-breaker constrain verify correct reviewer-agent forbidden-commands require-human-approval on-failure step-order-assertion parallelism-assertion plan-completion-assertion json-schema linter-check test-runner linter reviewer harness))
  (define harness-kw2 (cons '#:harness harness-kw))
  (define multiagent-kw '(#:routes #:steps #:branches #:reducer #:planner-prompt #:topology #:workers))
  (define multiagent-sym '(routes steps branches reducer planner-prompt topology workers multiagent))
  (define multiagent-kw2 (cons '#:multiagent multiagent-kw))
  (define kw->block (make-hash))
  (for-each (lambda (k) (hash-set! kw->block k ':model)) (append model-kw2 model-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':tools)) (append tools-kw tools-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':context)) (append context-kw context-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':harness)) (append harness-kw2 harness-sym))
  (for-each (lambda (k) (hash-set! kw->block k ':multiagent)) (append multiagent-kw2 multiagent-sym))
  ;; US-27：剥前导冒号（与 /ct 版同因）。
  (define (canon-k k)
    (define s (cond ((keyword? k) (keyword->string k))
                    ((symbol? k) (symbol->string k))
                    (else (format "~a" k))))
    (string->keyword (if (regexp-match? #rx"^:" s) (substring s 1) s)))
  (define buckets (make-hash))
  ;; B-06：块头键 + 列表值 = 整块内容（与 /ct 版同因）。
(define (block-items ck v)
    ;; B-06：块头键的值怎么摊进块，按块形状定：
    ;;   :tools      一个 clause        -> (tag v)
    ;;   :harness    clause 列表        -> (tag . v)
    ;;   :context    plist（:k v ...）  -> (tag . v)
    (cond
      [(eq? ck '#:tools) (list v)]
      [(eq? ck '#:harness) (if (and (list? v) (pair? v) (list? (car v))) v (list v))]
      [(eq? ck '#:context) (if (and (list? v) (pair? v) (keyword? (car v))) v (list v))]
      [(list? v) v]
      [else (list v)]))
  (define block-heads '(#:model #:tools #:context #:harness #:multiagent))
  ;; B-06：这些键由 append-pattern 收进 (:pattern :params ...)，不进块。
  (define pattern-keys '(#:routes #:steps #:branches #:reducer #:planner-prompt))
  (define (add! tag items)
    (hash-update! buckets tag (lambda (old) (append old items)) (lambda () (list tag))))
  (let loop ((xs plist))
    (cond
      ((null? xs) (void))
      ((null? (cdr xs)) (void))
      (else
       (let* ((k (car xs)) (v (cadr xs)) (ck (canon-k k)))
         (define tag (cond
                      ((hash-has-key? kw->block ck) (hash-ref kw->block ck))
                      (else ':unknown)))
         (cond
           ((memv ck pattern-keys) (void))
           ((and (memv ck block-heads) (list? v)) (add! tag (block-items ck v)))
           ;; B-06：:model-name 下游只认 :name。
           (else (add! tag (if (eq? ck '#:model-name) (list ':name v) (list k v)))))
         (loop (cddr xs))))))
  (for/list ((tag (in-list '(:model :tools :context :harness :multiagent :unknown)))
             #:when (hash-has-key? buckets tag))
    (hash-ref buckets tag)))

(define (ensure-blocks blocks)
  ;; US-27：标签统一成符号（与 /ct 版同因）。
  ;; B-06：:harness 也是必需块（与 /ct 版同因）。
  (define required '(:model :tools :context :harness))
  (define (block-tag b)
    (define t (and (pair? b) (car b)))
    (cond ((keyword? t) (string->symbol (string-append ":" (keyword->string t))))
          ((symbol? t) (string->symbol (if (regexp-match? #rx"^:" (symbol->string t)) (symbol->string t) (string-append ":" (symbol->string t)))))
          (else ':notablock)))
  (define existing-tags (map block-tag blocks))
  (define to-add (filter (lambda (tag) (not (memv tag existing-tags))) required))
  ;; B-06：缺块时给可用默认（与 /ct 版同因）。
  (define (default-block tag)
    (cond
      [(eq? tag ':model)
       '(:model :provider "openai" :name "gpt-5.6" :temperature 0.0
                :system-prompt "通用的任务执行 Agent。")]
      [(eq? tag ':tools) '(:tools (import-builtin bash))]
      [(eq? tag ':harness)
       '(:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
                  (:verify :json-schema #t :linter-check #f :test-runner "")
                  (:correct :max-retries 2 :circuit-breaker 3 :on-failure 'abort))]
      [(eq? tag ':context)
       '(:context :memory-policy (:markdown-fs "./memory/default.md"
                                  :layers (L0-Abstract) :auto-append #f))]
      [else (list tag)]))
  ;; B-06：用户只写 :model-name 时也要有 provider（下游必需）。
  (define (ensure-model b)
    (if (eq? (block-tag b) ':model)
        (let* ([b1 (if (memv ':provider b) b (append b (list ':provider "openai")))]
               [b2 (if (memv ':name b1) b1 (append b1 (list ':name "gpt-5.6")))])
          (if (memv ':system-prompt b2) b2 (append b2 (list ':system-prompt "通用的任务执行 Agent。"))))
        b))
  (define (ensure-context b)
    (if (and (eq? (block-tag b) ':context) (not (memv ':memory-policy b)))
        (append b (list ':memory-policy
                        '(:markdown-fs "./memory/default.md"
                          :layers (L0-Abstract) :auto-append #f)))
        b))
  (define new-blocks (append blocks (map default-block to-add)))
  (filter (lambda (b) (not (null? b))) (map ensure-context (map ensure-model new-blocks))))

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
                     :on-failure 'fallback-model))
           ;; CR-42 P-3：模式块必须是 :harness 的兄弟节点（放进 :harness 内会被 parse-harness 拒绝）
           ;; kind 必须已在 compiler/pattern_registry.rkt 注册
           (:pattern :kind reflect
                     :config (:markers ("失败即进入反思—修正回路"
                                        "reviewer-agent 复核后才算完成"
                                        "超过 :max-retries 次即中止"))
                     :params (:reviewer-agent "检查代码逻辑漏洞"))))
   ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (append-pattern/ct
                     (reorder-blocks/ct (ensure-blocks/ct (plist->blocks/ct rst-datum)))
                     'reflect
                     (list "失败即进入反思—修正回路" "reviewer-agent 复核后才算完成" "超过 :max-retries 次即中止")
                     (plist-filter/ct rst-datum '(reviewer-agent)))))
       (with-syntax (((blk ...) (datum->syntax #'here blocks)))
         #`(list 'define-agent '#,name-sym 'blk ...))))))

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
         ;; CR-42 P-3：模式语义进 AST（模式块是 :harness 的兄弟节点）
         (:pattern :kind router
                     :config (:markers ("按用户意图分发至正确 Worker"
                                      "路由判定先于任何工具执行"))
                     :params (:routes ("deploy=>ops")))
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
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (append-pattern/ct
                     (reorder-blocks/ct (ensure-blocks/ct (plist->blocks/ct rst-datum)))
                     'router
                     (list "按用户意图分发至正确 Worker" "路由判定先于任何工具执行")
                     (plist-filter/ct rst-datum '(routes)))))
       (with-syntax (((blk ...) (datum->syntax #'here blocks)))
         #`(list 'define-agent '#,name-sym 'blk ...))))))

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
顺序断言：Step1 的 summary 必须出现在 Step2 的代码请求之前（trajectory 时间顺序）。
PROMPT
                       ))
       #`(quote (defagent doc-pipeline
           (:model :provider "anthropic"
                   :name "claude-3-7-sonnet"
                   :temperature 0.0
                   :system-prompt sp)
           (:tools (import-builtin bash pytest))
           ;; CR-42 P-3：模式语义进 AST
           (:pattern :kind chain
                     :config (:markers ("步骤按给定顺序执行，不得跳过"
                                        "每步 :out 注入后续 :in 上下文"
                                        "最终 Answer 汇总为 JSON"))
                     :params (:steps ("plan" "act")))
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
                      :test-runner "")
             (:correct :max-retries 2 :circuit-breaker 5 :on-failure 'abort))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (append-pattern/ct
                     (reorder-blocks/ct (ensure-blocks/ct (plist->blocks/ct rst-datum)))
                     'chain
                     (list "步骤按给定顺序执行，不得跳过" "每步 :out 注入后续 :in 上下文" "最终 Answer 汇总为 JSON")
                     (plist-filter/ct rst-datum '(steps)))))
       (with-syntax (((blk ...) (datum->syntax #'here blocks)))
         #`(list 'define-agent '#,name-sym 'blk ...))))))

(define-syntax (defparallel-agent stx)
  (syntax-case stx ()
    ((_ name* . rst*)
     (free-identifier=? #'multi-search #'name*)
     #''(defagent multi-search
         (:model :provider "anthropic"
                 :name "claude-3-7-sonnet"
                 :temperature 0.0
                 :system-prompt "你是一个并行分支协调器（Parallelization Coordinator）。所有 :branches 下的 Worker 将被同时拉起，不得串行；全部结束后将各 Worker 结果交给 :reducer aggregator-agent 归并。并行断言：search-a 与 search-b 的轮次允许在 trajectory 时间线上交错。")
         (:tools (import-builtin bash read-pdf))
         ;; CR-42 P-3：模式语义进 AST
         (:pattern :kind parallel
                     :config (:markers ("所有分支同时拉起，不得串行"
                                      "分支轮次允许在轨迹时间线交错"
                                      "全部结束后交给 reducer 归并"))
                     :params (:branches ("a" "b")))
         (:context :memory-policy (:markdown-fs "./memory/multi-search.md"
                                   :layers ('L0-Abstract)
                                   :auto-append #f)
                   :skills ()
                   :status-bar (:step-count #t :current-branch #f :test-status #t))
         (:harness
           (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
           (:verify :json-schema #t
                    :linter-check #f
                    :test-runner "")
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
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (append-pattern/ct
                     (reorder-blocks/ct (ensure-blocks/ct (plist->blocks/ct rst-datum)))
                     'parallel
                     (list "所有分支同时拉起，不得串行" "分支轮次允许在轨迹时间线交错" "全部结束后交给 reducer 归并")
                     (plist-filter/ct rst-datum '(branches)))))
       (with-syntax (((blk ...) (datum->syntax #'here blocks)))
         #`(list 'define-agent '#,name-sym 'blk ...))))))

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
计划断言：计划步骤数必须 ∈ (3, 5)；FIN 阶段的 unfinished 列表必须为空。
PROMPT
                       ))
       #`(quote (defagent deep-researcher
           (:model :provider "anthropic"
                   :name "claude-3-7-sonnet"
                   :temperature 0.7
                   :system-prompt sp)
           (:tools (import-builtin web-search read-pdf))
           ;; CR-42 P-3：模式语义进 AST
           (:pattern :kind planner
                     :config (:markers ("首部输出计划 JSON，步骤数 ∈ (3,5)"
                                        "按计划逐步执行"
                                        "FIN 阶段报告完成度，unfinished 必须为空"))
                     :params (:plan-size 3))
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
                      :test-runner "")
             (:correct :max-retries 3 :circuit-breaker 5 :on-failure 'ask-human))))))
    ((_ name* . rst*)
     (let* ((name-sym (syntax->datum #'name*))
            (rst-datum (syntax->datum #'rst*))
            (blocks (append-pattern/ct
                     (reorder-blocks/ct (ensure-blocks/ct (plist->blocks/ct rst-datum)))
                     'planner
                     (list "首部输出计划 JSON，步骤数 ∈ (3,5)" "按计划逐步执行" "FIN 阶段报告完成度，unfinished 必须为空")
                     (plist-filter/ct rst-datum '(plan-size)))))
       (with-syntax (((blk ...) (datum->syntax #'here blocks)))
         #`(list 'define-agent '#,name-sym 'blk ...))))))

;;; =====================================================================

;;; =====================================================================
;;; CR-42 后续：核心语法糖宏（规格 §3.3-12 记忆管理、§3.5-20 多智能体协作）
;;; 这两个模式由核心语法承载。宏只封装默认值与形状，不新增核心键。
;;; 关键参数走 (:pattern :kind … :config …)，因而可被静态断言。
;;; 实现要点：块用 list 构造（不用 quasiquote），避免嵌套 unquote 陷阱。
;;; =====================================================================

;; 这些助手在宏展开期（phase 1）被调用，必须放在 begin-for-syntax 内。
;; 教训（台账 #9）：放模块顶层会报 reference to an unbound identifier。
(begin-for-syntax

(define (sugar-model prompt)
  (list ':model ':provider "anthropic" ':name "claude-3-7-sonnet" ':temperature 0.2
        ':system-prompt prompt))

(define (sugar-tools)
  (list ':tools (list 'import-builtin 'bash)))

(define (sugar-context store layers auto-append)
  (list ':context ':memory-policy
        (list ':markdown-fs store ':layers (map string->symbol layers) ':auto-append auto-append)
        ':skills '()
        ':status-bar (list ':step-count #t ':current-branch #f ':test-status #f)))

(define (sugar-harness)
  (list ':harness
        (list ':constrain ':require-human-approval '() ':forbidden-commands (list "rm -rf"))
        (list ':verify ':json-schema #t ':linter-check #f ':test-runner "")
        (list ':correct ':max-retries 2 ':circuit-breaker 5 ':on-failure 'abort)))

(define (sugar-worker name)
  (if (string? name)
      (list 'scoped-worker (string->symbol name)
            (sugar-model "子 Agent：执行被分派的子任务。")
            (sugar-tools)
            (sugar-harness))
      (list 'scoped-worker name
            (sugar-model "子 Agent：执行被分派的子任务。")
            (sugar-tools)
            (sugar-harness))))

) ; end begin-for-syntax

;;; 说明：两个宏构造纯 datum（不用 quasiquote），避免嵌套 unquote 与括号计数陷阱。
;;; 展开结果形如 (quote (define-agent NAME BLOCK ...))，与 V1 宏的产物形态一致。

(define-syntax (defmemory-agent stx)
  (syntax-case stx ()
    ((_ name store gc)
     (and (identifier? (syntax name))
          (string? (syntax->datum (syntax store)))
          (exact-positive-integer? (syntax->datum (syntax gc))))
     (let* ((nm (syntax->datum (syntax name)))
            (store-v (syntax->datum (syntax store)))
            (gc-v (syntax->datum (syntax gc)))
            (blocks
             (list (sugar-model "你是记忆管理 Agent（Memory Management）。三层加载记忆，超限即回收。")
                   (sugar-tools)
                   ;; 层枚举必须与 parser 的白名单一致：L0-Abstract / L1-Overview / L2-FullText
                   (sugar-context store-v '("L0-Abstract" "L1-Overview" "L2-FullText") #t)
                   (sugar-harness)
                   (list ':pattern ':kind 'memory
                         ':config (list ':store store-v ':context-window-gc gc-v)))))
       (datum->syntax stx (list 'quote (cons 'define-agent (cons nm blocks))))))
    ((_ . rest)
     (raise-syntax-error 'defmemory-agent
                         "用法：(defmemory-agent NAME STORE-PATH WINDOW-SIZE)"))))

(define-syntax (defmultiagent stx)
  (syntax-case stx ()
    ((_ name topology workers ...)
     (and (identifier? (syntax name))
          (memq (syntax->datum (syntax topology)) '(peer orchestration decentralised judge-driven))
          (pair? (syntax->list (syntax (workers ...)))))
     (let* ((nm (syntax->datum (syntax name)))
            (topo (syntax->datum (syntax topology)))
            (names (map syntax->datum (syntax->list (syntax (workers ...)))))
            (workers-block (list ':multiagent ':topology topo ':workers (map sugar-worker names)))
            (pattern-block (list ':pattern ':kind 'multi-agent
                                 ':config (list ':topology topo
                                                ':workers (map symbol->string names))))
            (blocks
             (list (sugar-model "你是多智能体协作团队的主控，负责分派与汇总。")
                   (sugar-tools)
                   (sugar-context "./memory/team.md" '("L0-Abstract") #f)
                   (sugar-harness)
                   workers-block
                   pattern-block)))
       (datum->syntax stx (list 'quote (cons 'define-agent (cons nm blocks))))))
    ((_ . rest)
     (raise-syntax-error 'defmultiagent
                         "用法：(defmultiagent NAME TOPOLOGY WORKER ...)"))))
