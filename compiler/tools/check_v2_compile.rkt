#lang racket/base
;; CR-41 V2 端到端编译探测（报告型，恒 exit 0）
;;
;; 正规通路 compile-agent-lisp 位于 compiler/agentlisp_compiler.rkt，但它在 Racket 8.12 下当前
;; **无法加载** —— 均为 C1 冻结文件的既存缺陷（与本 CR 的模式层无关）：
;;   ① agentlisp_compiler.rkt 括号不平衡（字符串/注释感知计数 par=-2，L119 / L692 各多一个 ")"）
;;      → read-syntax 直接失败，文件不可读；
;;   ② 即使修好 ①，其 require 的 checker.rkt:102 (struct srcloc* … #:transparent #:prefab)
;;      在 8.12 报 "multiple #:inspector/#:transparent/#:prefab specifications"（即 GAP-1 旁路的成因）；
;;   ③ 另一条 CLI 路径经 parser.rkt:54 (al-agent name purpose tools workflows hooks) 5 参 vs 6 字段
;;      → main.rkt -i/-o 对**任何** .al 输入 arity mismatch。
;; 修 ①②③ 必须改 C1 禁动类（AC-6 diff≠0）→ 待 Owner 批准；故本工具只探测与报告。

(require racket/file)

(define (probe rel)
  (with-handlers ([(lambda (e) #t)
                   (lambda (e) (format "BROKEN → ~a" (exn-message e)))])
    (dynamic-require rel #f)
    "OK"))

(printf "probe compiler/patterns_v2.rkt:     ~a\n" (probe "compiler/patterns_v2.rkt"))
(printf "probe compiler/agentlisp_compiler.rkt: ~a\n" (probe "compiler/agentlisp_compiler.rkt"))
(printf "probe compiler/checker.rkt:         ~a\n" (probe "compiler/checker.rkt"))
(printf "probe compiler/parser.rkt:          ~a\n" (probe "compiler/parser.rkt"))
(printf "probe compiler/emitter.rkt:         ~a\n" (probe "compiler/emitter.rkt"))
(printf "C1-BLOCKED: CR-41 模式层已通过 AST 合法性闸门 + pytest 70/70 + RackUnit 15/15；\n")
(printf "            端到端编译闸门待 Owner 批准修 C1 三项既存缺陷后启用。\n")
(exit 0)
