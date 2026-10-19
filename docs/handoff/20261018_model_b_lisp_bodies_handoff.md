# 模型 B：节点体用 Lisp 写，编译成 Python（2026-10-18）

> 目标：写 agent 只用 `.al`，编译出自包含 Python，作者不写 `.py`。

---

## 1. 结论

**跑通了。** 4 节点工作流的节点体全部用 Lisp 写，编译成 Python 函数，桥直接执行。零手写 Python。

---

## 2. 做了什么

| 组件 | 作用 |
|---|---|
| `runtime/al_core.py` | 产物调用的辅助库（hash-ref / format / py-call …） |
| `compiler/lisp_py.rkt` | Lisp 表达式 → Python 源码（语句位 / 表达式位分开发射） |
| `:body` 节点槽 | 节点体直接写 Lisp，编译器发射 `_al_node_<名>` 函数 |
| `WORKFLOW['body']` | 放**函数对象**，不走 import 路径（避免模块名依赖文件名） |
| 桥 | `_resolve` 优先用 `body`；`:handler` 仍是逃逸口 |

---

## 3. 支持的核心子集

| 类别 | 形式 |
|---|---|
| 特殊形式 | `if` `cond` `let` `let*` `begin` `and` `or` `not` `lambda` `quote` |
| 算术比较 | `+ - * /` `< > <= >=` `= equal? string=?` |
| 字典 | `hash` `hash-ref` `hash-set` `hash-keys` `hash-has-key?` |
| 字符串 | `format` `string-append` `string-split` `string-contains?` `string-upcase` `string-join` |
| 列表 | `first` `rest` `list-ref` `length` `append` `cons` `map` `filter` `foldl` `null?` |
| 宿主互操作 | `py/import` `py/call` `py/attr` `py/method` |

**完备性靠 `py/call` 兜底**：超出子集的，直接调 Python 库，但仍写在 `.al` 里。

---

## 4. 实测

```lisp
(draft :type computation
       :body (let ((f (hash-ref state "facts")))
               (hash "draft" (format "营收 ~a，净利率 ~a"
                                     (hash-ref f "revenue") (hash-ref f "margin"))))
       :output-fields (draft))
```

编译成：

```python
def _al_node_draft(state):
    f = _al.hash_ref(state, "facts")
    return _al.al_hash("draft", _al.al_format("营收 ~a，净利率 ~a",
                         _al.hash_ref(f, "revenue"), _al.hash_ref(f, "margin")))
```

运行结果：

```
facts   : {'revenue': 138000, 'margin': -1.4}
draft   : 营收 138000，净利率 -1.4
gate_ok : True
report  : 结论：营收 138000，净利率 -1.4
```

---

## 5. 验证

| 项 | 结果 |
|---|---|
| `tests/test_lisp_bodies.py` | 5 passed（编译产物合法 Python / 端到端跑通 / py-call / 互斥 / 缺体报错） |
| 产物 | `ast.parse` 通过；含 `_al_node_*` 函数 |
| `:handler` 与 `:body` 同给 | 编译期拒绝 |

---

## 6. 已知边界

| 项 | 说明 |
|---|---|
| 无尾调用优化 | Python 没有；深递归会炸。用 `foldl`/`map` 代替 |
| 顶层 `define`（辅助函数） | **未做**，当前只能内联 |
| 宏 | **未做**。编译器本身在 Racket 里，未来可先 `expand` 再发射 |
| 表达式位 `begin` | 只允许单表达式 |

---

## 7. 与复刻的关系

六个复刻项目的 `handlers/*.py` 现在可以用 `:body` 改写成 Lisp。

**预计残量**：每个项目从「N 个 handler 文件」降到「1-3 个工具」（真正碰世界的部分）。
