#lang racket/base
;; lisp_py.rkt — agentLisp 的「表达式 → Python」编译器（模型 B 核心）
;;
;; 目标：让 .al 里能写真正的 Lisp 代码（节点体、辅助函数），编译成 Python 源码，
;;       作者不写 .py 文件。完备性靠 (py/call ...) 宿主互操作兜底。
;;
;; 设计取舍：
;;   1. 不做解释器。产物是可读、可调试的 Python 源码。
;;   2. 只支持一个封闭的核心子集（见 lisp_py_supported），超出就报错并指明改写方式。
;;   3. 语句位与表达式位分开处理：let/begin 生成语句，if 生成条件表达式。

(require racket/list racket/string racket/format)

(provide lisp->py-expr lisp->py-defun lisp->py-body py-string lit->py)

;; ---------- 名字 ----------
;; Racket 标识符 -> Python 标识符。
;; 注意：Racket 的 #rx"..." 仍是字符串字面量，? 是非法转义，用字符类代替。
(define (mangle sym)
  (define s (symbol->string sym))
  (define s1 (regexp-replace* #rx"[?]$" s "_p"))
  (define s2 (regexp-replace* #rx"[!]$" s1 "_bang"))
  (define s3 (regexp-replace* #rx"[-?]" s2 "_"))
  (define s4 (regexp-replace* #rx"_+" s3 "_"))
  (if (regexp-match? #rx"^[0-9]" s4) (string-append "v_" s4) s4))

(define PY-RESERVED
  '("class" "def" "return" "if" "else" "elif" "for" "while" "in" "is" "not"
    "and" "or" "None" "True" "False" "lambda" "import" "from" "as" "with"
    "try" "except" "finally" "raise" "pass" "global" "nonlocal" "del" "yield"))

(define (py-name sym)
  (define n (mangle sym))
  (if (member n PY-RESERVED) (string-append n "_") n))

(define (py-string s)
  (format "~s" (if (string? s) s (format "~a" s))))

(define (lit->py v)
  (cond
    [(number? v) (if (exact-integer? v) (format "~a" v) (format "~a" (exact->inexact v)))]
    [(string? v) (py-string v)]
    [(boolean? v) (if v "True" "False")]
    [(char? v) (py-string (string v))]
    [(and (list? v) (null? v)) "[]"]
    [(and (pair? v) (eq? (car v) 'quote))
     (let ([d (cadr v)])
       (cond [(symbol? d) (py-string (symbol->string d))]
             [(null? d) "[]"]
             [(list? d) (format "[~a]" (string-join (map lit->py d) ", "))]
             [else (py-string (format "~a" d))]))]
    [else (py-string (format "~a" v))]))

;; ---------- 核心函数映射 ----------
(define INFIX '(+ - * /))
(define CMP-INFIX '(< > <= >=))

(define (core-fn sym)
  (case sym
    [(hash-ref) "_al.hash_ref"]
    [(hash-set) "_al.hash_set"]
    [(hash) "_al.al_hash"]
    [(hash-keys) "_al.hash_keys"]
    [(hash-has-key?) "_al.hash_has_key"]
    [(format) "_al.al_format"]
    [(string-append) "_al.string_append"]
    [(string-split) "_al.string_split"]
    [(string-contains?) "_al.string_contains"]
    [(string-upcase) "_al.string_upcase"]
    [(string-downcase) "_al.string_downcase"]
    [(string-join) "_al.string_join"]
    [(first car) "_al.first"]
    [(rest cdr) "_al.rest"]
    [(list-ref) "_al.list_ref"]
    [(length) "_al.length"]
    [(append) "_al.al_append"]
    [(cons) "_al.al_cons"]
    [(map) "_al.map_list"]
    [(filter) "_al.filter_list"]
    [(foldl) "_al.foldl"]
    [(null? empty?) "_al.null_p"]
    [(error) "_al.al_error"]
    [(llm llm-complete) "_al.llm_complete"]
    [(py/import) "_al.py_import"]
    [(py/call) "_al.py_call"]
    [(py/attr) "_al.py_attr"]
    [(py/method) "_al.py_method"]
    [(list vector) "_al_list"]
    [else #f]))

(define (emit-call head args)
  (define (arg e) (lisp->py-expr e))
  (cond
    ;; 列表字面量
    [(eq? head 'list) (format "[~a]" (string-join (map arg args) ", "))]
    [(eq? head 'vector) (format "[~a]" (string-join (map arg args) ", "))]
    ;; 四则
    [(eq? head '+) (if (null? args) "0" (format "(~a)" (string-join (map arg args) " + ")))]
    [(eq? head '-)
     (cond [(null? args) "0"]
           [(null? (cdr args)) (format "(- ~a)" (arg (car args)))]
           [else (format "(~a)" (string-join (map arg args) " - "))])]
    [(eq? head '*) (if (null? args) "1" (format "(~a)" (string-join (map arg args) " * ")))]
    [(eq? head '/)
     (cond [(null? args) "1"]
           [(null? (cdr args)) (format "(1 / ~a)" (arg (car args)))]
           [else (format "(~a)" (string-join (map arg args) " / "))])]
    ;; 比较（链式）
    [(member head CMP-INFIX)
     (format "(~a)" (string-join (map arg args) (format " ~a " head)))]
    [(member head '(= equal? string=? eq?))
     (format "_al.equal(~a)" (string-join (map arg args) ", "))]
    [(member head '(not equal-not))
     (format "_al.al_not(~a)" (arg (car args)))]
    ;; and / or 短路
    [(eq? head 'and) (if (null? args) "True" (format "(~a)" (string-join (map arg args) " and ")))]
    [(eq? head 'or) (if (null? args) "False" (format "(~a)" (string-join (map arg args) " or ")))]
    [else
     (define target (or (core-fn head) (py-name head)))
     (format "~a(~a)" target (string-join (map arg args) ", "))]))

;; ---------- 表达式 ----------
(define (lisp->py-expr e)
  (cond
    [(null? e) "[]"]
    [(symbol? e) (py-name e)]   ; 符号 = 变量引用（不是字符串）
    [(not (pair? e)) (lit->py e)]
    [(eq? (car e) 'quote) (lit->py e)]
    [(eq? (car e) 'if)
     (define parts (cdr e))
     (cond
       ;; Python 语法是 (THEN if COND else ELSE)：顺序不能写反（实测写反会把真假分支对调）
       [(= (length parts) 3)
        (format "(~a if ~a else ~a)" (lisp->py-expr (cadr parts))
                (lisp->py-expr (car parts)) (lisp->py-expr (caddr parts)))]
       [(= (length parts) 2)
        (format "(~a if ~a else None)" (lisp->py-expr (cadr parts)) (lisp->py-expr (car parts)))]
       [else (error 'lisp->py-expr "if 需要 2 或 3 个分支")])]
    [(eq? (car e) 'cond)
     (define clauses (cdr e))
     (define (clause->expr cl)
       (cond
         [(and (pair? cl) (eq? (car cl) 'else))
          (lisp->py-expr (if (null? (cdr cl)) #f (cadr cl)))]
         [(and (pair? cl) (pair? (cdr cl)))
          (format "(~a if ~a else ~a)"
                  (lisp->py-expr (cadr cl)) (lisp->py-expr (car cl))
                  (clause->expr (car (cdr (member cl clauses))))) ] ; placeholder, replaced below
         [else "None"]))
     ;; 从后往前折叠，避免 member 的线性查找
     (define (fold cls acc)
       (if (null? cls)
           acc
           (let* ([cl (car cls)]
                  [rest-acc (fold (cdr cls) #f)])
             (cond
               [(and (pair? cl) (eq? (car cl) 'else))
                (lisp->py-expr (if (null? (cdr cl)) #f (cadr cl)))]
               [(and (pair? cl) (pair? (cdr cl)))
                (format "(~a if ~a else ~a)"
                        (lisp->py-expr (cadr cl)) (lisp->py-expr (car cl))
                        (if rest-acc rest-acc "None"))]
               [else rest-acc]))))
     (or (fold clauses #f) "None")]
    [(eq? (car e) 'lambda)
     (define params (map py-name (cadr e)))
     (define body (cddr e))
     (format "(lambda ~a: ~a)"
             (string-join params ", ")
             (if (= (length body) 1) (lisp->py-expr (car body)) (lisp->py-expr (cons 'begin body))))]
    [(eq? (car e) 'begin)
     ;; 表达式位的 begin：用 Python 的括号 + 逗号不成立，退回单个表达式约束
     (if (= (length (cdr e)) 1)
         (lisp->py-expr (cadr e))
         (error 'lisp->py-expr "表达式位的 begin 只支持单个表达式；多语句请用 let 或节点体"))]
    [(eq? (car e) 'not) (emit-call 'not (cdr e))]
    [(and (pair? (car e)) (eq? (caar e) 'lambda))
     ;; ((lambda (x) ...) arg) -> 立即调用
     (format "(~a)(~a)" (lisp->py-expr (car e))
             (string-join (map lisp->py-expr (cdr e)) ", "))]
    [(symbol? (car e)) (emit-call (car e) (cdr e))]
    [else (error 'lisp->py-expr (format "无法编译的表达式：~s" e))]))

;; ---------- 语句 ----------
;; emit-into：逐条发射；最后一条交给 last-fn（决定「return」还是「丢弃」）。
(define (let-assigns bindings)
  (for/list ([b (in-list bindings)])
    (format "~a = ~a" (py-name (car b)) (lisp->py-expr (cadr b)))))

(define (emit-into forms last-fn)
  (cond
    [(null? forms) '()]
    [(null? (cdr forms)) (emit-last (car forms) last-fn)]
    [else (append (emit-stmt (car forms)) (emit-into (cdr forms) last-fn))]))

(define (emit-last f last-fn)
  (cond
    [(and (pair? f) (memq (car f) '(let let*)))
     (append (let-assigns (cadr f)) (emit-into (cddr f) last-fn))]
    [(and (pair? f) (eq? (car f) 'begin)) (emit-into (cdr f) last-fn)]
    [else (last-fn f)]))

(define (emit-stmt f)
  (cond
    [(and (pair? f) (memq (car f) '(let let*)))
     (append (let-assigns (cadr f))
             (emit-into (cddr f) (lambda (x) (list (format "_ = ~a" (lisp->py-expr x))))))]
    [(and (pair? f) (eq? (car f) 'begin))
     (emit-into (cdr f) (lambda (x) (list (format "_ = ~a" (lisp->py-expr x)))))]
    [else (list (lisp->py-expr f))]))

(define (lisp->py-body-lines forms)
  (if (null? forms)
      '()
      (emit-into forms (lambda (f) (list (format "return ~a" (lisp->py-expr f)))))))

;; ---------- 对外 ----------
;; (def <name>(<params>): <body>)
(define (lisp->py-defun name params forms)
  (define plist (map py-name params))
  (define body-lines (if (null? forms) (list "return None") (lisp->py-body-lines forms)))
  (string-append
   (format "def ~a(~a):\n" (py-name name) (string-join plist ", "))
   (string-join (for/list ([l (in-list body-lines)]) (format "    ~a" l)) "\n")
   "\n"))

;; 节点体：绑定 state
(define (lisp->py-body forms)
  (lisp->py-defun (gensym 'body) '(state) forms))
