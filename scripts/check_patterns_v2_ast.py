#!/usr/bin/env python3
"""CR-41 V2 gate: every pattern expansion must be a LEGAL AgentLisp Core AST.

Mirrors the closed grammar of compiler/agentlisp_compiler.rkt (allowlists + enums) so the
check runs locally without Racket; CI additionally compiles the same fixtures end-to-end.

Checks per fixture (10 patterns x HC/GENERIC/REVERSE = 30):
  1. top-level is (define-agent NAME <blocks>...)
  2. block sequence is a subsequence of (:model :tools :context :harness :multiagent) in
     ascending order, with the three mandatory buckets present
  3. :model   keys <= {:provider :name :temperature :system-prompt}; provider in PROVIDER-ENUM;
              temperature in [0,1]
  4. :tools   non-empty; clauses are (import-builtin ...) | (import-mcp "str") | (define-tool ...)
  5. :context keys <= {:memory-policy :skills :status-bar :compression};
              :memory-policy == (:markdown-fs "str" :layers (<enum>...) :auto-append bool),
              layers are BARE symbols from MEMORY-LAYER-ENUM (to-str does not unwrap quote);
              :status-bar keys <= {:step-count :current-branch :test-status :time-tracker :todo-list}
  6. :harness exactly (:harness (:constrain ..) (:verify ..) (:correct ..)) with the parser's
              per-section allowlists and enum/range checks
  7. :multiagent exactly (:multiagent :topology T :workers W), T in TOPOLOGY-ENUM, workers are
              (scoped-worker NAME (:model ..) (:tools ..) (:harness ..))
  8. committed .expected.rkt is byte-identical to what scripts/gen_patterns_v2.py regenerates
  9. the pattern's SRS markers are present in the system prompt (requirement traceability)

Exit 0 = all good; exit 1 = violations (printed).
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_patterns_v2 import FIX, PATTERNS, Sym, instantiate, read_al, sexp, template_of  # noqa: E402

PROVIDER_ENUM = ["anthropic", "openai", "qwen", "mock"]
TOPOLOGY_ENUM = ["peer", "orchestration", "decentralised", "judge-driven"]
ON_FAILURE_ENUM = ["ask-human", "fallback-model", "abort"]
LAYER_ENUM = ["L0-Abstract", "L1-Overview", "L2-FullText"]
BUCKET_ORDER = [":model", ":tools", ":context", ":harness", ":multiagent"]
MODEL_KEYS = {":provider", ":name", ":temperature", ":system-prompt"}
CONTEXT_KEYS = {":memory-policy", ":skills", ":status-bar", ":compression"}
CONSTRAIN_KEYS = {":require-human-approval", ":forbidden-commands", ":workspace-root"}
VERIFY_KEYS = {":json-schema", ":linter-check", ":test-runner", ":reviewer-agent"}
CORRECT_KEYS = {":max-retries", ":circuit-breaker", ":on-failure"}
STATUS_KEYS = {":step-count", ":current-branch", ":test-status", ":time-tracker", ":todo-list"}


def tag(block):
    return str(block[0]) if isinstance(block, list) and block else None


def kv_keys(block):
    return [str(x) for x in block[1:] if isinstance(x, str) and str(x).startswith(":")]


def check_model(block, where, errs):
    keys = set(kv_keys(block))
    bad = keys - MODEL_KEYS
    if bad:
        errs.append(f"{where}: :model 非法键 {sorted(bad)}")
    d = {}
    i = 1
    while i + 1 < len(block):
        d[str(block[i])] = block[i + 1]
        i += 2
    p = d.get(":provider")
    if p not in PROVIDER_ENUM:
        errs.append(f"{where}: :provider={p!r} 不在 {PROVIDER_ENUM}")
    t = d.get(":temperature")
    if not isinstance(t, int) and not isinstance(t, float):
        errs.append(f"{where}: :temperature={t!r} 必须是数字")
    elif not (0.0 <= float(t) <= 1.0):
        errs.append(f"{where}: :temperature={t!r} 超出 [0,1]")
    for k in (":name", ":system-prompt"):
        if not isinstance(d.get(k), str):
            errs.append(f"{where}: {k} 必须是字符串（Python SyntaxError 风险）")


def check_tools(block, where, errs):
    clauses = block[1:]
    if not clauses:
        errs.append(f"{where}: :tools 至少要有一种工具源")
    for c in clauses:
        if not isinstance(c, list) or not c:
            errs.append(f"{where}: :tools 子句非法 {c!r}")
            continue
        head = str(c[0])
        if head == "import-builtin":
            if not all(isinstance(x, str) for x in c[1:]) or len(c) < 2:
                errs.append(f"{where}: import-builtin 形如 (import-builtin name ...)")
        elif head == "import-mcp":
            if len(c) != 2 or not isinstance(c[1], str):
                errs.append(f"{where}: import-mcp 需要 1 个字符串 URL")
        elif head == "define-tool":
            if len(c) != 4:
                errs.append(f"{where}: define-tool 需要 3 个参数")
        else:
            errs.append(f"{where}: :tools 未知工具源 {head!r}")


def check_context(block, where, errs):
    keys = set(kv_keys(block))
    bad = keys - CONTEXT_KEYS
    if bad:
        errs.append(f"{where}: :context 非法键 {sorted(bad)}")
    mp = None
    sb = None
    i = 1
    while i + 1 < len(block):
        if str(block[i]) == ":memory-policy":
            mp = block[i + 1]
        if str(block[i]) == ":status-bar":
            sb = block[i + 1]
        i += 2
    if mp is None:
        errs.append(f"{where}: :context 缺 :memory-policy")
    else:
        if not isinstance(mp, list) or str(mp[0]) != ":markdown-fs":
            errs.append(f"{where}: :memory-policy 必须以 :markdown-fs 开头，得到 {mp!r}")
        else:
            if len(mp) != 6 or str(mp[2]) != ":layers" or str(mp[4]) != ":auto-append":
                errs.append(f"{where}: :memory-policy 必须恰好 (:markdown-fs PATH :layers (..) :auto-append BOOL)")
            else:
                if not isinstance(mp[1], str):
                    errs.append(f"{where}: markdown-fs path 必须是字符串")
                layers = mp[3]
                if not isinstance(layers, list) or not layers:
                    errs.append(f"{where}: :layers 必须是非空列表")
                else:
                    for l in layers:
                        if not isinstance(l, Sym) or str(l) not in LAYER_ENUM:
                            errs.append(f"{where}: layer {l!r} 非法（to-str 不拆 quote，必须裸符号且属于 {LAYER_ENUM}）")
                if not isinstance(mp[5], bool):
                    errs.append(f"{where}: :auto-append 必须是 #t/#f")
    if sb is not None:
        if not isinstance(sb, list):
            errs.append(f"{where}: :status-bar 形状非法 {sb!r}")
        else:
            bad = set(kv_keys(sb)) - STATUS_KEYS
            if bad:
                errs.append(f"{where}: :status-bar 非法键 {sorted(bad)}")


def check_harness(block, where, errs):
    if len(block) != 4:
        errs.append(f"{where}: :harness 必须恰好 3 个子句，得到 {len(block) - 1}")
        return
    c, v, co = block[1], block[2], block[3]
    if tag(c) != ":constrain":
        errs.append(f"{where}: :harness 第一子句必须是 :constrain")
    else:
        bad = set(kv_keys(c)) - CONSTRAIN_KEYS
        if bad:
            errs.append(f"{where}: :constrain 非法键 {sorted(bad)}")
    if tag(v) != ":verify":
        errs.append(f"{where}: :harness 第二子句必须是 :verify")
    else:
        bad = set(kv_keys(v)) - VERIFY_KEYS
        if bad:
            errs.append(f"{where}: :verify 非法键 {sorted(bad)}")
    if tag(co) != ":correct":
        errs.append(f"{where}: :harness 第三子句必须是 :correct")
    else:
        bad = set(kv_keys(co)) - CORRECT_KEYS
        if bad:
            errs.append(f"{where}: :correct 非法键 {sorted(bad)}")
        d = {}
        i = 1
        while i + 1 < len(co):
            d[str(co[i])] = co[i + 1]
            i += 2
        r = d.get(":max-retries")
        if not isinstance(r, int) or not (1 <= r <= 10):
            errs.append(f"{where}: :max-retries={r!r} 必须 1..10")
        b = d.get(":circuit-breaker")
        if not isinstance(b, int) or b <= 0:
            errs.append(f"{where}: :circuit-breaker={b!r} 必须是正整数")
        if d.get(":on-failure") not in ON_FAILURE_ENUM:
            errs.append(f"{where}: :on-failure={d.get(':on-failure')!r} 不在 {ON_FAILURE_ENUM}")


def check_multiagent(block, where, errs):
    if len(block) != 5 or str(block[1]) != ":topology" or str(block[3]) != ":workers":
        errs.append(f"{where}: :multiagent 必须恰好 (:multiagent :topology T :workers W)")
        return
    if str(block[2]) not in TOPOLOGY_ENUM:
        errs.append(f"{where}: :topology={block[2]!r} 不在 {TOPOLOGY_ENUM}（裸符号）")
    workers = block[4]
    if not isinstance(workers, list) or not workers:
        errs.append(f"{where}: :workers 必须是非空列表")
        return
    for w in workers:
        if not isinstance(w, list) or not w or str(w[0]) != "scoped-worker":
            errs.append(f"{where}: worker 必须是 (scoped-worker NAME ...)，得到 {w!r}")
            continue
        if len(w) != 5:
            errs.append(f"{where}: scoped-worker {w[1]} 必须恰好 4 块（name/model/tools/harness）")
            continue
        wname = w[1]
        if not isinstance(wname, Sym):
            errs.append(f"{where}: scoped-worker 名必须是符号")
        check_model(w[2], f"{where}/worker {wname}", errs)
        check_tools(w[3], f"{where}/worker {wname}", errs)
        check_harness(w[4], f"{where}/worker {wname}", errs)


def check_datum(datum, where, errs):
    if not isinstance(datum, list) or str(datum[0]) != "define-agent":
        errs.append(f"{where}: 顶层必须是 (define-agent NAME ...)")
        return None
    name = datum[1]
    blocks = datum[2:]
    tags = [tag(b) for b in blocks]
    if ":pattern-kind" in str(blocks) or ":pattern-config" in str(blocks):
        errs.append(f"{where}: 产物含非法的 :pattern-kind/:pattern-config")
    idxs = [BUCKET_ORDER.index(t) for t in tags if t in BUCKET_ORDER]
    if idxs != sorted(idxs):
        errs.append(f"{where}: 5 桶顺序不是升序：{tags}")
    unknown = [t for t in tags if t not in BUCKET_ORDER]
    if unknown:
        errs.append(f"{where}: 未知顶层块 {unknown}")
    for m in (":model", ":tools", ":context"):
        if m not in tags:
            errs.append(f"{where}: 缺三必块 {m}")
    for b in blocks:
        t = tag(b)
        if t == ":model":
            check_model(b, where, errs)
        elif t == ":tools":
            check_tools(b, where, errs)
        elif t == ":context":
            check_context(b, where, errs)
        elif t == ":harness":
            check_harness(b, where, errs)
        elif t == ":multiagent":
            check_multiagent(b, where, errs)
    return name


def main() -> int:
    errs = []
    n = 0
    for p in PATTERNS:
        markers = p["markers"]
        for scene in ("hc", "generic", "reverse"):
            al = FIX / f"{p['key']}_{scene}_{scene.upper()}.al"
            exp = FIX / f"{p['key']}_{scene}_{scene.upper()}.expected.rkt"
            where = f"{p['key']}_{scene.upper()}"
            form = read_al(al.read_text(encoding="utf-8"))
            datum = instantiate(template_of(p), form[1], form[2:])
            regenerated = sexp(datum)
            committed = "\n".join(exp.read_text(encoding="utf-8").splitlines()[1:]).strip()
            if committed != regenerated:
                errs.append(f"{where}: 提交的 .expected.rkt 与生成器不一致（fixture stale）")
            name = check_datum(datum, where, errs)
            if name is None or str(name) != str(form[1]):
                errs.append(f"{where}: 展开后 agent 名与输入不一致")
            blocks = datum[2:]
            model = next((b for b in blocks if tag(b) == ":model"), None)
            prompt = ""
            if model:
                i = 1
                while i + 1 < len(model):
                    if str(model[i]) == ":system-prompt":
                        prompt = model[i + 1]
                    i += 2
            for mk in markers:
                if mk not in prompt:
                    errs.append(f"{where}: system-prompt 缺 SRS 标记 {mk!r}")
            n += 1
    print(f"checked {n} fixtures")
    if errs:
        for e in errs:
            print("VIOLATION:", e)
        return 1
    print("PATTERNS V2 AST OK (30/30 legal Core AST)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
