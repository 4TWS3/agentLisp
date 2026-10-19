# srcloc 透传（语句级行号映射）：根因与修法

> 日期：2026-10-18
> 状态：**未落地**。根因已定位，修法已验证。

---

## 1. 目标

产物是 Python，报错行号对不上 `.al`。想要：

```
# al:23
return _al.al_hash("draft", ...)
```

再用 `scripts/al_traceback.py` 把 Python 行映射回 `.al` 第 23 行。

---

## 2. 根因（已实测验证）

用 `read-syntax` + `port-count-lines!` 读文件，建「datum pair → 行号」的 `eq?` 表。
**表的规模恒为 1**，遍历在第一层就停了。

原因：**`syntax-e` 对「列表形状」的语法对象返回 list，不是 pair**。

```racket
(define sx (syntax-e stx))
(pair? sx)   ; => #t（列表也是 pair）
(list? sx)   ; => #t
(syntax? (cdr sx))  ; => #f  ← 关键：cdr 是普通 list，不是 syntax
```

于是 `(rec (cdr sx) (cdr v))` 这一步 `(syntax? s)` 为假，递归终止。

实测（`/tmp/p3.rkt`）：

| 检查 | 结果 |
|---|---|
| `(syntax? stx)` | #t |
| `(pair? (syntax-e stx))` | #t |
| `(list? (syntax-e stx))` | #t |
| `(syntax? (car (syntax-e stx)))` | #t |

---

## 3. 修法

遍历必须**先判 list，再用 `in-list` 逐元素**，不能走 `car/cdr`：

```racket
(define (record-datum-lines! stx dat table)
  (when (and (syntax? stx) (pair? dat))
    (define ln (syntax-line stx))
    (when ln (hash-set! table dat ln))
    (define sx (syntax-e stx))
    (cond
      [(list? sx)
       (for ([s (in-list sx)] [d (in-list dat)])
         (record-datum-lines! s d table))]
      [(pair? sx)
       (record-datum-lines! (car sx) (car dat) table)
       (record-datum-lines! (cdr sx) (cdr dat) table)])))
```

其余部分（read-syntax 读取、`current-datum-lines` 参数、`# al:N` 发射、注入）逻辑正确，只是被这一个 bug 挡住。

---

## 4. 三处改动清单（下次照做）

| 文件 | 改动 |
|---|---|
| `compiler/main.rkt` | `file->value-list` 用 `read-syntax` + `port-count-lines!`，返回 `(values forms table)`；调用处 `define-values`；`(set-datum-lines! table)` |
| `compiler/lisp_py.rkt` | 新增 `current-datum-lines` 参数；`emit-into` 每条语句前插 `# al:<行>` |
| `compiler/agentlisp_compiler.rkt` | 把行号表传给 `parsed`（或由 main 注入） |

注意：**不能**经 `agentlisp_compiler` 的 `dynamic-require` 拿 `lisp_py` 的 parameter —— 它没 re-export。main.rkt 直接 `(require "lisp_py.rkt")` 用同一个实例。

---

## 5. 我犯的错

按「对象同一性」设计映射，**假设没验证就写了两百行**。
正确做法：先跑 10 行探针确认 `(eq? ...)` 成立，再动实现。

`/tmp/probe2.rkt` 那次探针本可以在 5 分钟内暴露问题，我却先改了三个文件。
