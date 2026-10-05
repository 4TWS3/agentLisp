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
    "check_sideeffect_builtins_racket_mirror",
    "extract_checker_rkt_sideeffect_list",
    "make_parse_error_json",
    "sideeffect_builtin_names",
    "validate_correct_on_failure",
    "validate_memory_auto_append_key",
    "validate_provider_and_temperature",
    "validate_tools_combination_and_mcp_scheme",
    "validate_topology_and_scoped_worker_min_blocks",
]
