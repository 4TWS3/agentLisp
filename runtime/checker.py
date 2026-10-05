"""AgentLisp v2 static-checker Python-side SSOT mirror.

Mirrors compiler/checker.rkt (Racket) invariants for runtime usage
(no Racket install needed on host when CI unavailable).

Racket SSOT (L87 compiler/checker.rkt):
  (define SIDEEFFECT-BUILTIN-TOOLS '(bash git-push wget curl scp dd chmod sudo))

Python SSOT (runtime/checker.py) must be a strict superset. If the two drift,
test_fr_check_2_sideeffect_builtins_ssot_consistent() will fail in CI.
"""

from __future__ import annotations

import re

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


__all__ = [
    "SIDEEFFECT_BUILTIN_TOOLS",
    "check_sideeffect_builtins_racket_mirror",
    "extract_checker_rkt_sideeffect_list",
    "sideeffect_builtin_names",
]
