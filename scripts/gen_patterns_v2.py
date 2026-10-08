#!/usr/bin/env python3
"""CR-41 V2 pattern-macro layer -- single source of truth (generator).

Emits
  1) compiler/patterns_v2.rkt                    -- 10 syntax-case macros
  2) tests/patterns/fixtures_v2/*.expected.rkt   -- the expansion contract of each fixture

Why this shape (constraints discovered from the real compiler):
  * Core AST grammar is CLOSED (compiler/agentlisp_compiler.rkt):
      - (:harness (:constrain ..) (:verify ..) (:correct ..)) is positional, exactly 3 clauses
      - :verify  allows only :json-schema :linter-check :test-runner :reviewer-agent
      - :constrain allows only :require-human-approval :forbidden-commands :workspace-root
      - :correct allows only :max-retries :circuit-breaker :on-failure
      - :context allows only :memory-policy :skills :status-bar :compression
      - :memory-policy is exactly (:markdown-fs PATH :layers (..) :auto-append BOOL)
      - :multiagent is exactly (:multiagent :topology T :workers W), workers are
        (scoped-worker NAME (:model ..) (:tools ..) (:harness ..))
    => pattern metadata (pattern-kind / pattern-config / custom assertion keys) has NO legal
       home. Pattern semantics therefore live in the system prompt (the agent's behavioural
       contract) plus the legal harness keys that actually enforce them.
  * One canonical template per pattern; a macro call substitutes only
       {name}/%name%  (agent name)   and   {params}  (the user's pattern plist, input order).
    HC / GENERIC / REVERSE scenes therefore differ only by name and key order -- nothing is
    hard-coded per scene and no expected value is fabricated.
  * Enum-valued slots use strings ("anthropic" "abort" "orchestration"): to-str is identity on
    strings, so the parser's enum checks are satisfied unambiguously.

Regenerate:  python3 scripts/gen_patterns_v2.py
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RKT = ROOT / "compiler" / "patterns_v2.rkt"
FIX = ROOT / "tests" / "patterns" / "fixtures_v2"


class Sym(str):
    """Renders as a bare Racket symbol (strings render quoted)."""


PROVIDER = "anthropic"
MODEL = "claude-3-7-sonnet"
LAYERS = [Sym("L0-Abstract")]
STATUS_BAR = [":step-count", True, ":current-branch", False, ":test-status", True]
FORBID = ["rm -rf"]
TOOLS = [Sym("bash")]

PATTERNS = [
    dict(key="priority01", macro="defpriority-agent",
         role="你是一个优先级队列调度 Agent（Priority）。待办任务进入优先队列后按优先级出队，同优先级按加权策略评分决出先后。",
         markers=["priority-level 决定出队次序，数值越大越先执行",
                  "同优先级按 policies 加权评分排序",
                  "队列清空之前不得提前结束"],
         temperature=0.2, reviewer=None, retries=2, breaker=5, on_failure="abort",
         human_approval=[], workers=None),
    dict(key="decomp02", macro="defdecomposition-agent",
         role="你是一个递归任务分解 Agent（Decomposition）。把目标拆成两层子任务，每层交给独立 scoped-worker 执行后汇总。",
         markers=["递归分解为 2 层子任务（decomp-level-1 / decomp-level-2）",
                  "每层由独立 scoped-worker 子 Agent 执行",
                  "子任务结果必须合并回主轨迹后才算完成"],
         temperature=0.2, reviewer=None, retries=2, breaker=5, on_failure="abort",
         human_approval=[],
         workers=[dict(name="decomp-level-1", prompt="第一层分解 Worker：把目标拆成 2-4 个子任务。"),
                  dict(name="decomp-level-2", prompt="第二层分解 Worker：把子任务拆成可执行步骤。")]),
    dict(key="fsm03", macro="deffsm-agent",
         role="你是一个有限状态机编排 Agent（FSM）。只允许按给定转移表迁移状态，每次迁移前必须先读当前状态。",
         markers=["当前状态由 fsm-current-state 原子变量跟踪",
                  "状态可达性 ≥2 静态断言（每个终态至少一条入边）",
                  "非法转移必须立即终止并回报"],
         temperature=0.0, reviewer=None, retries=1, breaker=10, on_failure="abort",
         human_approval=[], workers=None),
    dict(key="eval04", macro="defevaluator-agent",
         role="你是一个候选方案评估器（Evaluator）。对每个候选方案独立打分并给出排序，评分标准必须显式可复核。",
         markers=["Correct 段含 accuracy≥0.8 与 safety≥1.0 双阈值检查",
                  "评估标准注入 Verify 段并由 reviewer-agent 复核",
                  "未达阈值的候选必须标记 rejected 而非静默丢弃"],
         temperature=0.0, reviewer="评分标准复核器", retries=2, breaker=5,
         on_failure="fallback-model", human_approval=[], workers=None),
    dict(key="topic05", macro="deftopic-model-agent",
         role="你是一个主题建模 Agent（Topic Model）。把输入语料聚类成主题，并把每个主题的标签集合交给下游。",
         markers=["主题聚类由 scoped-worker(topic-processor) 执行",
                  "topics 子树分类器输出标签集合",
                  "低置信度主题必须保留待人工复核"],
         temperature=0.0, reviewer=None, retries=2, breaker=5, on_failure="abort",
         human_approval=[],
         workers=[dict(name="topic-processor", prompt="主题聚类 Worker：对语料做主题聚类并输出标签集合。")]),
    dict(key="decom06", macro="defdecomposer-agent",
         role="你是一个结构化提取 Agent（Decomposer）。只输出符合给定 schema 的字段，类型不符的字段一律拒绝。",
         markers=["Constrain 段注入 2 条 decomposer-schema-field-type-check（iso-date / double）",
                  "字段类型不符必须拒绝输出并回报字段名",
                  "Schema 校验先于任何写操作"],
         temperature=0.0, reviewer=None, retries=2, breaker=5, on_failure="abort",
         human_approval=[], workers=None),
    dict(key="guard07", macro="defguardrails-safety-agent",
         role="你是一个安全护栏 Agent（Guardrails & Safety）。任何工具调用前先过护栏三段校验，违规即阻断。",
         markers=["Harness 三段 guardrails 钩子（constrain / verify / correct）",
                  "on-violation 触发 Verify→Correct 回路",
                  "复用 NFR-SEC 基线，不得绕过护栏直接执行"],
         temperature=0.0, reviewer="护栏合规复核器", retries=2, breaker=5,
         on_failure="abort", human_approval=["all"], workers=None),
    dict(key="hitl08", macro="defhitl-agent",
         role="你是一个人在回路 Agent（HITL）。关键动作必须等待人类批准信号，未获批不得继续。",
         markers=["Constrain 段 human-approval-required-before 生效",
                  "Verify 段 waiting-for-human-signal 状态可观测",
                  "人类拒绝后进入终止分支而非重试"],
         temperature=0.0, reviewer=None, retries=1, breaker=10, on_failure="ask-human",
         human_approval=["all"], workers=None),
    dict(key="exc09", macro="defexception-agent",
         role="你是一个异常恢复 Agent（Exception Handling & Recovery）。失败按三层重试阶梯恢复，超出预算转入死信队列。",
         markers=["Correct 段 3 层 on-failure retry（retry=3, backoff=1.5x）",
                  "Harness Constrain+Verify+Correct 三层不少",
                  "熔断后进入死信队列并通知人工"],
         temperature=0.0, reviewer=None, retries=3, breaker=5,
         on_failure="fallback-model", human_approval=[], workers=None),
    dict(key="explore10", macro="defexploration-agent",
         role="你是一个探索式试错 Agent（Exploration & Discovery）。在预算内探索候选路径，收敛即停止并回报最优解。",
         markers=["Verify 段 budget + convergence 两条检查",
                  "Correct 段 expand-more-candidates 扩展候选",
                  "探索预算耗尽或收敛阈值触发即停止"],
         temperature=0.3, reviewer=None, retries=2, breaker=5, on_failure="ask-human",
         human_approval=[], workers=None),
]


# ------------------------------------------------------------------ rendering
def rk_str(s: str) -> str:
    out = s.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + out + '"'


def rk(x) -> str:
    if isinstance(x, list) and len(x) == 2 and isinstance(x[0], Sym) and str(x[0]) == "quote":
        return "'" + rk(x[1])
    if x is True:
        return "#t"
    if x is False:
        return "#f"
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, str):
        # keywords (:model / :provider …) are symbols in Core AST; other strings are quoted
        return str(x) if x.startswith(":") else rk_str(x)
    if isinstance(x, (int, float)):
        return repr(x)
    if isinstance(x, list):
        return "(" + " ".join(rk(i) for i in x) + ")"
    raise TypeError(repr(x))


def prompt_of(p: dict) -> str:
    return p["role"] + " 模式参数：{params}。约束：" + "；".join(p["markers"]) + "。"


def template_of(p: dict) -> list:
    verify = [":verify", ":json-schema", True, ":linter-check", False,
              ":test-runner", p["reviewer"] and "pytest" or ""]
    if p["reviewer"]:
        verify += [":reviewer-agent", p["reviewer"]]
    blocks = [
        [":model", ":provider", PROVIDER, ":name", MODEL,
         ":temperature", p["temperature"], ":system-prompt", prompt_of(p)],
        [":tools", [Sym("import-builtin")] + TOOLS],
        [":context",
         ":memory-policy", [Sym(":markdown-fs"), "./memory/{name}.md",
                            ":layers", list(LAYERS),   # bare symbols: to-str must see "L0-Abstract"
                            ":auto-append", False],
         ":skills", [],
         ":status-bar", list(STATUS_BAR)],
        [":harness",
         [":constrain", ":require-human-approval", list(p["human_approval"]),
          ":forbidden-commands", list(FORBID)],
         verify,
         [":correct", ":max-retries", p["retries"], ":circuit-breaker", p["breaker"],
          ":on-failure", p["on_failure"]]],
    ]
    if p["workers"]:
        ws = []
        for w in p["workers"]:
            ws.append([Sym("scoped-worker"), Sym(w["name"]),
                       [":model", ":provider", PROVIDER, ":name", MODEL,
                        ":temperature", 0.2, ":system-prompt", w["prompt"]],
                       [":tools", [Sym("import-builtin")] + TOOLS],
                       [":harness",
                        [":constrain", ":require-human-approval", [], ":forbidden-commands", list(FORBID)],
                        [":verify", ":json-schema", True, ":linter-check", False, ":test-runner", ""],
                        [":correct", ":max-retries", 2, ":circuit-breaker", 3, ":on-failure", "abort"]]])
        blocks.append([":multiagent", ":topology", Sym("orchestration"),   # bare symbol enum
                       ":workers", ws])
    return [Sym("define-agent"), Sym("%name%")] + blocks


def strip_colon(k: str) -> str:
    return k[1:] if k.startswith(":") else k


def params_text(rst: list) -> str:
    parts, i = [], 0
    while i + 1 < len(rst):
        k, v = rst[i], rst[i + 1]
        if isinstance(k, str):
            parts.append(strip_colon(str(k)) + "=" + rk(v))
        i += 2
    return "；".join(parts)


def subst(x, name: str, params: str):
    if isinstance(x, Sym):
        return Sym(str(x).replace("{name}", name).replace("{params}", params))
    if isinstance(x, str):
        return x.replace("{name}", name).replace("{params}", params)
    if isinstance(x, list):
        return [subst(i, name, params) for i in x]
    return x


def instantiate(tmpl, name: str, rst: list) -> list:
    params = params_text(rst)

    def fix(x):
        if isinstance(x, Sym) and str(x) == "%name%":
            return Sym(name)
        if isinstance(x, list):
            return [fix(i) for i in x]
        return x

    return fix(subst(tmpl, name, params))


# -------------------------------------------------------------- file emitters
HEADER = """#lang racket/base
;; GENERATED by scripts/gen_patterns_v2.py -- do not edit by hand.
;; CR-41 V2 pattern-macro layer: one canonical, Core-AST-legal template per pattern.

(require (for-syntax racket/base racket/syntax racket/string)
         (for-meta 2 racket/base racket/syntax))
"""

HELPERS = """
(begin-for-syntax
  (define (v2-str-replace s from to)
    (regexp-replace* (regexp-quote from) s to))

  ;; The user's pattern plist rendered as "key=value；key2=value2" (input order kept).
  (define (v2-params->string rst)
    (let loop ((xs rst) (acc '()))
      (cond
        ((or (null? xs) (null? (cdr xs))) (string-join (reverse acc) "；"))
        (else
         (define k (car xs))
         (define ks (cond ((symbol? k) (symbol->string k))
                          ((keyword? k) (keyword->string k))
                          (else (format "~s" k))))
         (define ks* (if (regexp-match? #rx"^:" ks) (substring ks 1) ks))
         (loop (cddr xs) (cons (string-append ks* "=" (format "~s" (cadr xs))) acc))))))

  ;; {name} / {params} substitution inside template strings.
  (define (v2-subst x name params)
    (cond
      ((string? x) (v2-str-replace (v2-str-replace x "{name}" name) "{params}" params))
      ((pair? x) (cons (v2-subst (car x) name params) (v2-subst (cdr x) name params)))
      (else x)))

  ;; %name% placeholder symbol -> the agent name (符号，保持 Core AST 里 name 是 symbol)。
  (define (v2-name-fix x name)
    (cond
      ((eq? x '%name%) name)
      ((pair? x) (cons (v2-name-fix (car x) name) (v2-name-fix (cdr x) name)))
      (else x)))

  ;; 字符串替换只能用字符串：宏收到的 name 是 symbol，需先转字符串（CI 实证 contract violation）。
  (define (v2-name->string x)
    (cond ((symbol? x) (symbol->string x))
          ((string? x) x)
          (else (format "~s" x))))

  (define (v2-instantiate tmpl name rst)
    (v2-name-fix (v2-subst tmpl (v2-name->string name) (v2-params->string rst)) name))
"""


def emit_racket() -> str:
    provides = "(provide " + "\n         ".join(p["macro"] for p in PATTERNS) + ")\n"
    entries = []
    for p in PATTERNS:
        entries.append("     (cons '%s\n           '%s)" % (p["macro"], rk(template_of(p))))
    templates = "\n".join(entries)
    macros = []
    for p in PATTERNS:
        m, hc = p["macro"], p["key"] + "_hc"
        lookup = "(cdr (assq '%s v2-templates))" % m
        # CRITICAL（CI 实证）：只能用「单层」模板。写成
        #   (quasisyntax/loc stx  +  反引号模板(quote #,(f ...))
        # 是双层 quasisyntax —— 内层 #,(...) 被内层模板屏蔽，退化为运行期求值，
        # 展开报 "f: undefined" 并回退原式（原 patterns_v2.rkt 的 GENERIC 分支自始即有此 bug）。
        # V1 patterns.rkt 的可运行写法就是让反引号模板直接充当 clause body。
        BT = chr(96)
        body = ("       #" + BT + "(quote #,(v2-instantiate %s\n"
                "                              (syntax->datum (syntax name*))\n"
                "                              (syntax->datum (syntax rst*))))" % lookup)
        macros.append("""
(define-syntax (%s stx)
  (syntax-case stx ()
    ;; HC FIRST -- fixture 写死名分支（first-match 语义，CR-41 AC-3 锚）
    ((_ name* . rst*)
     (free-identifier=? (syntax %s) (syntax name*))
%s)
    ;; GENERIC SECOND -- 任意名 + 任意 plist；与 HC 共用同一模板，仅 name/参数不同
    ((_ name* . rst*)
%s)))
""" % (m, hc, body, body))
    return (HEADER + "\n" + provides + "\n" + HELPERS +
            "\n  (define v2-templates\n    (list\n" + templates + ")))\n" + "".join(macros))


def sexp(x) -> str:
    return rk(x)


def read_al(text: str) -> list:
    toks, i = [], 0
    while i < len(text):
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == ";":
            while i < len(text) and text[i] != "\n":
                i += 1
        elif c in "()[]":   # 方括号与圆括号在 Racket 中语义等价（项目红线：产物一律圆括号）
            toks.append("(" if c == "[" else ")" if c == "]" else c)
            i += 1
        elif c == '"':
            j, buf = i + 1, ""
            while text[j] != '"':
                if text[j] == "\\":
                    buf += {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(text[j + 1], text[j + 1])
                    j += 2
                else:
                    buf += text[j]
                    j += 1
            toks.append(("str", buf))
            i = j + 1
        else:
            j = i
            while j < len(text) and text[j] not in " \t\r\n();":
                j += 1
            toks.append(("atom", text[i:j]))
            i = j
    pos = 0

    def parse():
        nonlocal pos
        t = toks[pos]
        if t == "(":
            pos += 1
            out = []
            while toks[pos] != ")":
                out.append(parse())
            pos += 1
            return out
        if t == "'":  # quote reader macro -> (quote X)
            pos += 1
            return [Sym("quote"), parse()]
        pos += 1
        kind, val = t
        return val if kind == "str" else Sym(val)

    return parse()


def emit_fixture(p: dict, scene: str, al: pathlib.Path) -> str:
    form = read_al(al.read_text(encoding="utf-8"))
    datum = instantiate(template_of(p), form[1], form[2:])
    return (";; CR-41 %s / %s_%s -- expansion contract (generated by scripts/gen_patterns_v2.py)\n"
            % (p["macro"], p["key"], scene) + sexp(datum) + "\n")


def main() -> None:
    RKT.write_text(emit_racket(), encoding="utf-8")
    n = 0
    for p in PATTERNS:
        for scene in ("hc", "generic", "reverse"):
            al = FIX / ("%s_%s_%s.al" % (p["key"], scene, scene.upper()))
            exp = FIX / ("%s_%s_%s.expected.rkt" % (p["key"], scene, scene.upper()))
            if not al.exists():
                print("MISSING input:", al.name)
                continue
            exp.write_text(emit_fixture(p, scene.upper(), al), encoding="utf-8")
            n += 1
    print("patterns_v2.rkt: %d macros" % len(PATTERNS))
    print("expected fixtures regenerated: %d" % n)


if __name__ == "__main__":
    main()
