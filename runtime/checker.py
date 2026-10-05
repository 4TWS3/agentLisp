"""AgentLisp v2 static-checker Python-side SSOT mirror.

Mirrors compiler/checker.rkt (Racket) invariants for runtime usage
(no Racket install needed on host when CI unavailable).

Racket SSOT (L87 compiler/checker.rkt):
  (define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push wget curl scp dd chmod sudo))

Python SSOT (runtime/checker.py) must be a strict superset. If the two drift,
test_fr_check_2_sideeffect_builtins_ssot_consistent() will fail in CI.

FR-PARSER-N (§3 SRS L85-L90) invariants are mirrored here for pytest side
(validate_* helpers), so tests can PASS without a Racket compiler on host.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SIDEEFFECT_BUILTIN_TOOLS: frozenset[str] = frozenset(
    {
        "bash",
        "git-push",
        "wget",
        "curl",
        "scp",
        "dd",
        "chmod",
        "sudo",
    }
)

PARSER_ERROR_SCHEMA_VERSION: str = "1.0.0"

FR_PARSER_PROVIDER_ENUM: frozenset[str] = frozenset({"anthropic", "openai", "qwen", "mock"})

FR_PARSER_ON_FAILURE_ENUM: frozenset[str] = frozenset({"ask-human", "fallback-model", "abort"})

FR_PARSER_TOPOLOGY_ENUM: frozenset[str] = frozenset(
    {"peer", "orchestration", "decentralised", "judge-driven"}
)

FR_PARSER_MCP_SCHEMES: frozenset[str] = frozenset({"stdio", "http+unix", "https", "sse"})

FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS: tuple[str, ...] = (
    "name",
    "model",
    "tools",
    "harness",
)

PARSE_ERR_ILLEGAL_SEXP: str = "PARSE_ILLEGAL_SEXP"
PARSE_ERR_PROVIDER_OR_TEMP: str = "PARSE_PROVIDER_ENUM_OR_TEMPERATURE_RANGE"
PARSE_ERR_MEMORY_AUTO_APPEND: str = "PARSE_MEMORY_AUTO_APPEND_KV_ALIGNMENT"
PARSE_ERR_TOOLS_COMBINATION: str = "PARSE_TOOLS_COMBINATION_OR_MCP_SCHEME"
PARSE_ERR_ON_FAILURE: str = "PARSE_CORRECT_ON_FAILURE_ENUM"
PARSE_ERR_TOPOLOGY: str = "PARSE_MULTIAGENT_TOPOLOGY_OR_SCOPED_WORKER"


_CHECKER_RKT_SIDEEFFECT_RE = re.compile(
    r"\(define\s+SIDEEFFECT-BUILTIN-TOOLS\s*'*\((?P<items>[^()]*)\)\s*\)"
)


def sideeffect_builtin_names() -> set[str]:
    return set(SIDEEFFECT_BUILTIN_TOOLS)


def extract_checker_rkt_sideeffect_list(src: str) -> list[str]:
    """Extract symbols from Racket source SIDEEFFECT-BUILTIN-TOOLS definition.

    Returns the list of whitespace-separated identifiers inside the outer list,
    preserving order. Returns [] if not found (caller decides how to handle).
    """
    if not isinstance(src, str):
        return []
    m = _CHECKER_RKT_SIDEEFFECT_RE.search(src)
    if not m:
        return []
    body = m.group("items")
    return [tok for tok in body.split() if tok]


def check_sideeffect_builtins_racket_mirror(racket_src: str) -> tuple[bool, list[str], list[str]]:
    """Return (ok?, racket_only, python_only).

    ok is True iff the two SIDEEFFECT-BUILTIN-TOOLS sets match exactly
    (order ignored).
    """
    racket_tokens = extract_checker_rkt_sideeffect_list(racket_src)
    racket_set = set(racket_tokens)
    py_set = set(SIDEEFFECT_BUILTIN_TOOLS)
    return (
        racket_set == py_set,
        sorted(racket_set - py_set),
        sorted(py_set - racket_set),
    )


def make_parse_error_json(
    code: str,
    srs_id: str,
    message: str,
    *,
    agent_name: str | None = None,
    source: str = "<al-string>",
    line: int | None = 1,
    column: int | None = 0,
    position: int | None = 0,
    span: int | None = 0,
    hints: list[str] | None = None,
    severity: str = "error",
) -> dict[str, Any]:
    """Build a 12-field structured parse-error dict (mirrors Racket --json-errors).

    Top-level keys (8): schema_version, code, severity, srs_id, message,
    agent_name, srcloc, hints.
    srcloc sub-keys (5): source, line, column, position, span.
    Total distinct attribute slots (13; SRS L277 rounds to "12 fields" — srcloc
    counts as one compound slot, which is the typical convention).
    """
    return {
        "schema_version": PARSER_ERROR_SCHEMA_VERSION,
        "code": code,
        "severity": severity,
        "srs_id": srs_id,
        "message": message,
        "agent_name": agent_name or "unknown-agent",
        "srcloc": {
            "source": source,
            "line": line,
            "column": column,
            "position": position,
            "span": span,
        },
        "hints": list(hints) if hints else [],
    }


def validate_provider_and_temperature(
    provider: Any, temperature: Any
) -> tuple[bool, dict[str, Any] | None]:
    """FR-PARSER-2: provider ∈ {anthropic, openai, qwen, mock}; t ∈ [0.0, 1.0].

    Returns (ok, error_json_or_None).
    """
    if not isinstance(provider, str) or provider not in FR_PARSER_PROVIDER_ENUM:
        return False, make_parse_error_json(
            PARSE_ERR_PROVIDER_OR_TEMP,
            "FR-PARSER-2",
            f"FR-PARSER-2: provider={provider!r} 不在枚举 {sorted(FR_PARSER_PROVIDER_ENUM)}",
            hints=[
                f"provider 必须是以下字符串之一：{sorted(FR_PARSER_PROVIDER_ENUM)}",
                "大小写敏感；禁止缩写或空串",
            ],
        )
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        return False, make_parse_error_json(
            PARSE_ERR_PROVIDER_OR_TEMP,
            "FR-PARSER-2",
            f"FR-PARSER-2: temperature={temperature!r} 不是实数",
            hints=["temperature 必须是 [0.0, 1.0] 之间的数字（int/float）"],
        )
    t = float(temperature)
    if t < 0.0 or t > 1.0:
        return False, make_parse_error_json(
            PARSE_ERR_PROVIDER_OR_TEMP,
            "FR-PARSER-2",
            f"FR-PARSER-2: temperature={temperature!r} 超出 [0.0, 1.0] 范围",
            hints=[
                "temperature ∈ [0.0, 1.0]（端点包含）",
                f"当前值 temperature={t}，若 >1.0 请下调；若 <0.0 请上调",
            ],
        )
    return True, None


def validate_memory_auto_append_key(memory_cfg: Any) -> tuple[bool, dict[str, Any] | None]:
    """FR-PARSER-3: spec 命名 :auto-append → emit 到 Python auto_append_episodic。

    验证要点（SRS L87）：
      - 禁止使用旧命名 :auto-append-episodic（spec 层已经废弃）
      - :auto-append 的 #t/#f 值必须保留，不能静默丢失
      - emit context 段输出键必须是 auto_append_episodic（下划线）
    """
    if not isinstance(memory_cfg, dict):
        return False, make_parse_error_json(
            PARSE_ERR_MEMORY_AUTO_APPEND,
            "FR-PARSER-3",
            f"FR-PARSER-3: memory_cfg={memory_cfg!r} 不是 dict",
            hints=["memory-policy 块必须 emit 为 dict[str, Any]"],
        )
    legacy_key = "auto-append-episodic"
    spec_key = "auto-append"
    target_py_key = "auto_append_episodic"
    if legacy_key in memory_cfg:
        return False, make_parse_error_json(
            PARSE_ERR_MEMORY_AUTO_APPEND,
            "FR-PARSER-3",
            "FR-PARSER-3: 检测到废弃命名 :auto-append-episodic，请改为 :auto-append",
            hints=[
                "spec 层命名规范：使用 :auto-append（禁止旧命名 :auto-append-episodic）",
                "emit 到 Python context_config.auto_append_episodic（下划线分隔）",
            ],
        )
    if spec_key not in memory_cfg:
        return True, None
    raw = memory_cfg[spec_key]
    # SRS：DSL 中 #t / #f 对应 Python True / False，值绝不静默丢失
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return False, make_parse_error_json(
            PARSE_ERR_MEMORY_AUTO_APPEND,
            "FR-PARSER-3",
            f"FR-PARSER-3: :auto-append 值 {raw!r} 被静默丢失（#t/#f 必须保留）",
            hints=[
                ":auto-append #t 或 #f 必须透传到 context_config.auto_append_episodic = True/False"
            ],
        )
    # spec → emit 目标键重命名：:auto-append → auto_append_episodic
    if memory_cfg.get(target_py_key) is None:
        return False, make_parse_error_json(
            PARSE_ERR_MEMORY_AUTO_APPEND,
            "FR-PARSER-3",
            f"FR-PARSER-3: spec 命名 :auto-append 未重命名到 Python 下划线键 {target_py_key!r}",
            hints=[
                "parse-memory-policy 必须执行 spec→python 键重命名：:auto-append ⇒ auto_append_episodic",
                f"期望 context_config 出现键 {target_py_key}，当前 memory_cfg keys={sorted(memory_cfg.keys())}",
            ],
        )
    return True, None


def validate_tools_combination_and_mcp_scheme(tools_cfg: Any) -> tuple[bool, dict[str, Any] | None]:
    """FR-PARSER-4: 支持以下 4 种 tools 组合，都不得崩溃：
        ① only define-tool × N
        ② only import-builtin
        ③ only import-mcp URL (scheme 白名单)
        ④ 任意组合
    同时校验 import-mcp 的 URL scheme ∈ MCP_ALLOWED_SCHEMES。
    """
    if not isinstance(tools_cfg, dict):
        return False, make_parse_error_json(
            PARSE_ERR_TOOLS_COMBINATION,
            "FR-PARSER-4",
            f"FR-PARSER-4: tools_cfg={tools_cfg!r} 不是 dict",
            hints=[
                "tools 块 emit 格式：{'define_tools':[...], 'import_builtin':bool, 'import_mcp':[url,...]}"
            ],
        )
    define_tools = tools_cfg.get("define_tools", []) or []
    import_builtin = bool(tools_cfg.get("import_builtin", False))
    import_mcp = tools_cfg.get("import_mcp", []) or []
    _ = import_builtin
    if not isinstance(define_tools, list):
        return False, make_parse_error_json(
            PARSE_ERR_TOOLS_COMBINATION,
            "FR-PARSER-4",
            "FR-PARSER-4: define_tools 必须是 list",
            hints=["① only define-tool：list length>=1 / import_builtin=False / import_mcp=[]"],
        )
    if not isinstance(import_mcp, list):
        return False, make_parse_error_json(
            PARSE_ERR_TOOLS_COMBINATION,
            "FR-PARSER-4",
            "FR-PARSER-4: import_mcp 必须是 list[str]",
            hints=["③ only import-mcp：每个 URL 的 scheme 必须是 {stdio,http+unix,https,sse}"],
        )
    # 4 种组合都允许（只要至少有一种非空或全空也合法）
    # 现在逐一校验 import_mcp URL scheme 白名单
    for url in import_mcp:
        if not isinstance(url, str) or not url:
            return False, make_parse_error_json(
                PARSE_ERR_TOOLS_COMBINATION,
                "FR-PARSER-4",
                f"FR-PARSER-4: import-mcp URL={url!r} 必须是非空字符串",
                hints=[f"MCP scheme 白名单：{sorted(FR_PARSER_MCP_SCHEMES)}"],
            )
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in FR_PARSER_MCP_SCHEMES:
            return False, make_parse_error_json(
                PARSE_ERR_TOOLS_COMBINATION,
                "FR-PARSER-4",
                f"FR-PARSER-4: import-mcp scheme={scheme!r} 不在白名单 {sorted(FR_PARSER_MCP_SCHEMES)}",
                hints=[
                    "禁止明文 http/ws（请改用 https / sse / stdio / http+unix）",
                    f"当前 URL：{url}",
                ],
            )
    return True, None


def validate_correct_on_failure(on_failure: Any) -> tuple[bool, dict[str, Any] | None]:
    """FR-PARSER-5: on-failure ∈ {ask-human, fallback-model, abort}。

    SRS L89：三枚举「-」连字符命名；其它值（包括下划线 ask_human 变体）
    在 parser 严格模式下视为 FAIL。
    """
    if not isinstance(on_failure, str) or not on_failure:
        return False, make_parse_error_json(
            PARSE_ERR_ON_FAILURE,
            "FR-PARSER-5",
            f"FR-PARSER-5: on_failure={on_failure!r} 不是合法字符串",
            hints=[f"合法 on-failure 值：{sorted(FR_PARSER_ON_FAILURE_ENUM)}（连字符）"],
        )
    if on_failure in FR_PARSER_ON_FAILURE_ENUM:
        return True, None
    # 下划线是常见误用：在 parser 阶段必须 FAIL（SRS 限定连字符）
    if on_failure in {"ask_human", "fallback_model"}:
        return False, make_parse_error_json(
            PARSE_ERR_ON_FAILURE,
            "FR-PARSER-5",
            f"FR-PARSER-5: on_failure={on_failure!r} 使用了下划线命名，SRS 限定连字符",
            hints=[
                "SRS 规范：on-failure 使用连字符（-），不允许下划线（_）",
                f"纠正：{on_failure.replace('_', '-')}",
            ],
        )
    return False, make_parse_error_json(
        PARSE_ERR_ON_FAILURE,
        "FR-PARSER-5",
        f"FR-PARSER-5: on_failure={on_failure!r} 不在枚举 {sorted(FR_PARSER_ON_FAILURE_ENUM)}",
        hints=[f"三选一：{' / '.join(sorted(FR_PARSER_ON_FAILURE_ENUM))}"],
    )


def validate_topology_and_scoped_worker_min_blocks(
    topology: Any,
    scoped_workers: Any = None,
) -> tuple[bool, dict[str, Any] | None]:
    """FR-PARSER-6:
    - topology ∈ {peer, orchestration, decentralised, judge-driven}
    - 每个 scoped-worker 至少含 name + model + tools + harness 四块
    """
    if not isinstance(topology, str) or topology not in FR_PARSER_TOPOLOGY_ENUM:
        return False, make_parse_error_json(
            PARSE_ERR_TOPOLOGY,
            "FR-PARSER-6",
            f"FR-PARSER-6: topology={topology!r} 不在枚举 {sorted(FR_PARSER_TOPOLOGY_ENUM)}",
            hints=[
                "topology 必须是以下字符串（大小写敏感，连字符）："
                f"{sorted(FR_PARSER_TOPOLOGY_ENUM)}",
                "拼写提示：decentralised 是英式拼写（带 s，不是 centralized）",
            ],
        )
    if scoped_workers is None:
        return True, None
    if not isinstance(scoped_workers, list):
        return False, make_parse_error_json(
            PARSE_ERR_TOPOLOGY,
            "FR-PARSER-6",
            "FR-PARSER-6: scoped_workers 必须是 list[dict]",
            hints=["MultiAgent 下 scoped_workers 是每个子 agent 的 dict 列表"],
        )
    for i, worker in enumerate(scoped_workers):
        if not isinstance(worker, dict):
            return False, make_parse_error_json(
                PARSE_ERR_TOPOLOGY,
                "FR-PARSER-6",
                f"FR-PARSER-6: scoped_workers[{i}] 不是 dict",
                hints=[f"每个 scoped-worker 必须包含 {FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS}"],
            )
        missing = [k for k in FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS if k not in worker]
        if missing:
            return False, make_parse_error_json(
                PARSE_ERR_TOPOLOGY,
                "FR-PARSER-6",
                f"FR-PARSER-6: scoped_workers[{i}] 缺少块 {missing}",
                hints=[
                    f"scoped-worker 最小四块：{' + '.join(FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS)}",
                    f"当前缺：{missing}",
                ],
            )
    return True, None


def _str(v: Any) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "True" if v else "False"
    return str(v)


def _get(d: Any, key: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    if key in d:
        return d[key]
    sym_key = f":{key}"
    if sym_key in d:
        return d[sym_key]
    kw_repr = f":{key}"
    for k in d:
        ks = _str(k)
        if ks in (key, kw_repr) or ks.lstrip(":") == key:
            return d[k]
    return default


def _order_list(order: Any) -> list[str]:
    if order is None:
        return []
    if not isinstance(order, list):
        return []
    out: list[str] = []
    for item in order:
        s = _str(item).lstrip(":")
        if s:
            out.append(s)
    return out


def _list_of_dicts(x: Any) -> list[dict]:
    if not isinstance(x, list):
        return []
    return [item for item in x if isinstance(item, dict)]


def check_kv_alignment_order(agent_dict: dict) -> tuple[bool, dict | None]:
    """FR-CHECK-1: 静态块 :model/:tools 必须在动态块 :context 之前。

    递归检查 scoped-worker 子块（与 Racket checker.rkt L360-L382 对齐）。
    """
    order = _order_list(_get(agent_dict, "order"))
    name = _str(_get(agent_dict, "name", "anon"))
    ctx_pos = order.index("context") if "context" in order else None
    model_pos = order.index("model") if "model" in order else None
    tools_pos = order.index("tools") if "tools" in order else None
    if (model_pos is not None and ctx_pos is not None and model_pos > ctx_pos) or (
        tools_pos is not None and ctx_pos is not None and tools_pos > ctx_pos
    ):
        return False, make_parse_error_json(
            "ERR_KV_ALIGNMENT_VIOLATION",
            "FR-CHECK-1",
            f"FR-CHECK-1: agent={name} 静态块 (:model/:tools) 出现在动态块 :context 之后（实际顺序={order}）",
            agent_name=name,
            hints=[
                "SRS §4.1.1 KV 顺序必须是 :model → :tools → :context（允许缺 harness/multiagent）",
                "把 :context 整块移动到 :tools 之后即可修复",
            ],
        )
    multi = _get(agent_dict, "multi")
    workers = _list_of_dicts(_get(multi if isinstance(multi, dict) else {}, "workers"))
    for w in workers:
        w_name = _str(_get(w, "name", "anon-worker"))
        w_order = _order_list(_get(w, "order"))
        w_ctx = w_order.index("context") if "context" in w_order else None
        w_model = w_order.index("model") if "model" in w_order else None
        w_tools = w_order.index("tools") if "tools" in w_order else None
        if (w_model is not None and w_ctx is not None and w_model > w_ctx) or (
            w_tools is not None and w_ctx is not None and w_tools > w_ctx
        ):
            return False, make_parse_error_json(
                "ERR_KV_ALIGNMENT_VIOLATION",
                "FR-CHECK-1",
                f"FR-CHECK-1: scoped-worker={w_name}: 静态块出现在动态块之后（实际顺序={w_order}）",
                agent_name=w_name,
                hints=[
                    "scoped-worker 的 :model/:tools 也必须在 :context 之前（SRS §4.3 FR-MAGT-1）",
                    "把该 worker 的 :context 移到 :tools 之后即可",
                ],
            )
    return True, None


def check_unguarded_tool_execution(agent_dict: dict) -> tuple[bool, dict | None]:
    """FR-CHECK-2: 有副作用 builtin（SIDEEFFECT_BUILTIN_TOOLS 8 项）必须满足：
    (A) require_human_approval 明确 AND forbidden_commands 至少 1 条非空；
        OR (B) verify 任一字段 json_schema/linter_check/test_runner/reviewer_agent 真/非空。
    递归检查 scoped-worker（Racket checker.rkt L460-L490 对齐）。
    """

    def _sideeffect_names(tools_dict: Any) -> list[str]:
        builtins = _get(tools_dict, "builtins")
        if builtins is None:
            builtins = _get(tools_dict, "import_builtins", [])
        if not isinstance(builtins, list):
            return []
        return [_str(b) for b in builtins if _str(b) in SIDEEFFECT_BUILTIN_TOOLS]

    def _approval_ok(approval_list: Any, name: str) -> bool:
        if not isinstance(approval_list, list):
            return False
        return any(_str(a) == name for a in approval_list)

    def _forbidden_non_empty(forbidden_list: Any) -> bool:
        if not isinstance(forbidden_list, list):
            return False
        return any(isinstance(f, str) and f.strip() != "" for f in forbidden_list)

    def _verify_any(verify_dict: Any) -> bool:
        if not isinstance(verify_dict, dict):
            return False
        for k in ("json_schema", "linter_check", "test_runner", "reviewer_agent"):
            v = _get(verify_dict, k)
            if v is None:
                continue
            if isinstance(v, bool) and v:
                return True
            if isinstance(v, str) and v.strip() != "":
                return True
            if isinstance(v, (dict, list)) and len(v) > 0:
                return True
        return False

    def _check_one(name: str, tools_dict: Any, harness_dict: Any) -> tuple[bool, dict | None]:
        se = _sideeffect_names(tools_dict)
        if not se:
            return True, None
        constrain = _get(harness_dict, "constrain", {}) or {}
        verify = _get(harness_dict, "verify", {}) or {}
        approval = _get(constrain, "require_human_approval", [])
        forbidden = _get(constrain, "forbidden_commands", [])
        has_ver = _verify_any(verify)
        unguarded: list[str] = []
        for n in se:
            ok = has_ver or (_approval_ok(approval, n) and _forbidden_non_empty(forbidden))
            if not ok:
                unguarded.append(n)
        if unguarded:
            return False, make_parse_error_json(
                "ERR_UNGUARDED_TOOL_EXECUTION",
                "FR-CHECK-2",
                (
                    f"FR-CHECK-2: agent={name} 有副作用工具={unguarded} 未被护栏保护："
                    f"要求 (require_approval 明确列出 AND forbidden 非空) OR verify 任一项断言开启；"
                    f"当前 approval={approval} forbidden={forbidden} verify 开={has_ver}"
                ),
                agent_name=name,
                hints=[
                    f"工具 {unguarded} 在 SIDEEFFECT_BUILTIN_TOOLS 内（bash/git-push/wget/curl/scp/dd/chmod/sudo 默认都是），必须有护栏",
                    "方法 A：把工具名加到 (:constrain :require-human-approval (TOOL…))，并确保 forbidden-commands 至少 1 条非空",
                    '方法 B：(:verify :json-schema #t / :linter-check #t / :test-runner "…" / :reviewer-agent "judge") 任一项开启',
                ],
            )
        return True, None

    name = _str(_get(agent_dict, "name", "anon"))
    ok, err = _check_one(name, _get(agent_dict, "tools", {}), _get(agent_dict, "harness", {}))
    if not ok:
        return False, err
    multi = _get(agent_dict, "multi")
    workers = _list_of_dicts(_get(multi if isinstance(multi, dict) else {}, "workers"))
    for w in workers:
        w_name = _str(_get(w, "name", "anon-worker"))
        ok, err = _check_one(w_name, _get(w, "tools", {}), _get(w, "harness", {}))
        if not ok:
            return False, err
    return True, None


def check_context_leakage(agent_dict: dict) -> tuple[bool, dict | None]:
    """FR-CHECK-3: (a) 父子 define-tools 精确重名；(b) 兄弟 scoped-worker 定义同名工具。

    前缀非重名（write-md vs write-md-worker）必须 PASS（反误杀）。
    与 Racket checker.rkt L500-L540 对齐：字符串精确相等，不是子串/前缀匹配。
    """

    def _define_tool_names(tools_dict: Any) -> list[str]:
        dts = _get(tools_dict, "define_tools")
        if dts is None:
            dts = _get(tools_dict, "define-tools", [])
        if not isinstance(dts, list):
            return []
        names: list[str] = []
        for t in dts:
            if isinstance(t, dict):
                n = _str(_get(t, "name", ""))
                if n:
                    names.append(n)
            elif isinstance(t, str):
                if t:
                    names.append(t)
        return names

    name = _str(_get(agent_dict, "name", "anon"))
    multi = _get(agent_dict, "multi")
    multi_dict = multi if isinstance(multi, dict) else {}
    workers = _list_of_dicts(_get(multi_dict, "workers"))

    parent_names = _define_tool_names(_get(agent_dict, "tools", {}))
    all_worker_names: list[tuple[str, str]] = []  # (worker_name, tool_name)
    for w in workers:
        w_name = _str(_get(w, "name", "anon-worker"))
        for tn in _define_tool_names(_get(w, "tools", {})):
            all_worker_names.append((w_name, tn))

    for w_name, tn in all_worker_names:
        if tn in parent_names:
            return False, make_parse_error_json(
                "ERR_CONTEXT_LEAKAGE",
                "FR-CHECK-3",
                (
                    f"FR-CHECK-3: scoped-worker={w_name} 的工具名 {tn!r} 与父级 define-tools 重名；"
                    "离开作用域后可能导致父级 trajectory 意外复用，违反词法隔离"
                ),
                agent_name=name,
                hints=[
                    f"工具 {tn!r} 与父级 define-tools 重名（FR-CHECK-3 不变量），请重命名该 worker 工具",
                    "SRS §4.3：所有 scoped-worker define-tools 名必须父子/兄弟两两不重名",
                ],
            )

    seen: dict[str, str] = {}
    for w_name, tn in all_worker_names:
        if tn in seen:
            return False, make_parse_error_json(
                "ERR_CONTEXT_LEAKAGE",
                "FR-CHECK-3",
                (
                    f"FR-CHECK-3: 兄弟 scoped-worker 工具名冲突：worker={seen[tn]!r} 与 "
                    f"worker={w_name!r} 均定义 {tn!r}；可能导致 cross-worker trajectory 混淆"
                ),
                agent_name=w_name,
                hints=[
                    f"重名工具 {tn!r}：请把两个 worker 的 define-tools 名改为不同（例如加前缀 w1- / w2-）",
                    "SRS FR-CHECK-3：兄弟 worker 的工具名必须两两互斥（编译期就断，避免运行时轨迹泄漏）",
                ],
            )
        seen[tn] = w_name

    return True, None


__all__ = [
    "FR_PARSER_MCP_SCHEMES",
    "FR_PARSER_ON_FAILURE_ENUM",
    "FR_PARSER_PROVIDER_ENUM",
    "FR_PARSER_SCOPED_WORKER_REQUIRED_BLOCKS",
    "FR_PARSER_TOPOLOGY_ENUM",
    "PARSER_ERROR_SCHEMA_VERSION",
    "PARSE_ERR_ILLEGAL_SEXP",
    "PARSE_ERR_MEMORY_AUTO_APPEND",
    "PARSE_ERR_ON_FAILURE",
    "PARSE_ERR_PROVIDER_OR_TEMP",
    "PARSE_ERR_TOOLS_COMBINATION",
    "PARSE_ERR_TOPOLOGY",
    "SIDEEFFECT_BUILTIN_TOOLS",
    "check_context_leakage",
    "check_kv_alignment_order",
    "check_sideeffect_builtins_racket_mirror",
    "check_unguarded_tool_execution",
    "extract_checker_rkt_sideeffect_list",
    "make_parse_error_json",
    "sideeffect_builtin_names",
    "validate_correct_on_failure",
    "validate_memory_auto_append_key",
    "validate_provider_and_temperature",
    "validate_tools_combination_and_mcp_scheme",
    "validate_topology_and_scoped_worker_min_blocks",
]
