"""CR-34 O4 AC-1: Python 端 3 defs × 循环内 6 cases = 18 scenarios，与 Racket test_checker_ac1.rkt 字节位对齐。

严格基线 Δ=+3（127→130 passed），不使用 @pytest.mark.parametrize 展开，
保证 --collect-only 3 tests collected。
"""

from __future__ import annotations

import pytest

from runtime.checker import (
    check_context_leakage,
    check_kv_alignment_order,
    check_unguarded_tool_execution,
)

KV_CASES: list[tuple[str, dict, bool, str | None]] = [
    ("KV-1neg", {"name": "a", "order": ["context", "model"]}, False, "ERR_KV_ALIGNMENT_VIOLATION"),
    ("KV-2neg", {"name": "b", "order": ["context", "tools"]}, False, "ERR_KV_ALIGNMENT_VIOLATION"),
    (
        "KV-3neg",
        {"name": "c", "order": ["model", "context", "tools"]},
        False,
        "ERR_KV_ALIGNMENT_VIOLATION",
    ),
    (
        "KV-4neg",
        {"name": "d", "order": ["tools", "context", "model"]},
        False,
        "ERR_KV_ALIGNMENT_VIOLATION",
    ),
    ("KV-5pos", {"name": "e", "order": ["model", "tools", "context"]}, True, None),
    ("KV-6pos", {"name": "f", "order": ["model", "tools", "harness", "context"]}, True, None),
]


UN_CASES: list[tuple[str, dict, bool, str | None]] = [
    (
        "UN-1neg",
        {
            "name": "u1",
            "tools": {"import_builtins": ["git-push"]},
            "harness": {"constrain": {}, "verify": {}},
        },
        False,
        "ERR_UNGUARDED_TOOL_EXECUTION",
    ),
    (
        "UN-2neg",
        {
            "name": "u2",
            "tools": {"import_builtins": ["bash"]},
            "harness": {
                "constrain": {"require_human_approval": ["bash"], "forbidden_commands": []},
                "verify": {},
            },
        },
        False,
        "ERR_UNGUARDED_TOOL_EXECUTION",
    ),
    (
        "UN-3neg",
        {
            "name": "u3",
            "tools": {"import_builtins": ["curl"]},
            "harness": {
                "constrain": {"require_human_approval": ["curl"], "forbidden_commands": ["", "  "]},
                "verify": {},
            },
        },
        False,
        "ERR_UNGUARDED_TOOL_EXECUTION",
    ),
    (
        "UN-4neg",
        {
            "name": "u4",
            "tools": {"import_builtins": ["sudo"]},
            "harness": {
                "constrain": {
                    "require_human_approval": ["bash"],
                    "forbidden_commands": ["rm -rf /"],
                },
                "verify": {},
            },
        },
        False,
        "ERR_UNGUARDED_TOOL_EXECUTION",
    ),
    (
        "UN-5pos",
        {
            "name": "u5",
            "tools": {"import_builtins": ["git-push"]},
            "harness": {
                "constrain": {
                    "require_human_approval": ["git-push"],
                    "forbidden_commands": ["git push --force"],
                },
                "verify": {},
            },
        },
        True,
        None,
    ),
    (
        "UN-6pos",
        {
            "name": "u6",
            "tools": {"import_builtins": ["bash"]},
            "harness": {"constrain": {}, "verify": {"test_runner": "pytest"}},
        },
        True,
        None,
    ),
]


CL_CASES: list[tuple[str, dict, bool, str | None]] = [
    (
        "CL-1neg",
        {
            "name": "p1",
            "tools": {"define_tools": [{"name": "write-md"}]},
            "multi": {
                "workers": [{"name": "w1", "tools": {"define_tools": [{"name": "write-md"}]}}]
            },
        },
        False,
        "ERR_CONTEXT_LEAKAGE",
    ),
    (
        "CL-2neg",
        {
            "name": "p2",
            "tools": {"define-tools": [{"name": "read-xls"}]},
            "multi": {
                "workers": [{"name": "w1", "tools": {"define_tools": [{"name": "read-xls"}]}}]
            },
        },
        False,
        "ERR_CONTEXT_LEAKAGE",
    ),
    (
        "CL-3neg",
        {
            "name": "p3",
            "tools": {},
            "multi": {
                "workers": [
                    {"name": "w1", "tools": {"define_tools": [{"name": "check-rule"}]}},
                    {"name": "w2", "tools": {"define_tools": [{"name": "check-rule"}]}},
                ]
            },
        },
        False,
        "ERR_CONTEXT_LEAKAGE",
    ),
    (
        "CL-4neg",
        {
            "name": "p4",
            "tools": {},
            "multi": {
                "workers": [
                    {"name": "w1", "tools": {"define_tools": ["run-shell"]}},
                    {"name": "w2", "tools": {"define_tools": ["run-shell"]}},
                ]
            },
        },
        False,
        "ERR_CONTEXT_LEAKAGE",
    ),
    (
        "CL-5pos",
        {
            "name": "p5",
            "tools": {"define_tools": [{"name": "write-md"}]},
            "multi": {
                "workers": [
                    {"name": "w1", "tools": {"define_tools": [{"name": "write-md-worker"}]}}
                ]
            },
        },
        True,
        None,
    ),
    (
        "CL-6pos",
        {
            "name": "p6",
            "tools": {"define_tools": [{"name": "father"}]},
            "multi": {
                "workers": [
                    {"name": "w1", "tools": {"define_tools": [{"name": "a"}]}},
                    {"name": "w2", "tools": {"define_tools": [{"name": "b"}]}},
                    {"name": "w3", "tools": {"define_tools": [{"name": "c"}]}},
                ]
            },
        },
        True,
        None,
    ),
]


@pytest.mark.req("AC-1")
@pytest.mark.req("FR-CHECK-1")
def test_ac1_kv_alignment_6cases_roundtrip() -> None:
    """KV 顺序不变量：4 反例 ERR_KV_ALIGNMENT_VIOLATION + 2 正例 PASS。"""
    results: list[bool] = []
    for case_id, agent, exp_ok, exp_code in KV_CASES:
        ok, err = check_kv_alignment_order(agent)
        assert ok == exp_ok, f"{case_id}: ok={ok} != {exp_ok} err={err}"
        if not exp_ok:
            assert err is not None and err.get("code") == exp_code
        else:
            assert err is None
        results.append(True)
        print(f"[AC-1] {case_id}_PASS")
    assert all(results) and len(results) == 6


@pytest.mark.req("AC-1")
@pytest.mark.req("FR-CHECK-2")
def test_ac1_unguarded_tool_6cases_roundtrip() -> None:
    """副作用工具双护栏不变量：4 反例 ERR_UNGUARDED_TOOL_EXECUTION + 2 正例 PASS。"""
    results: list[bool] = []
    for case_id, agent, exp_ok, exp_code in UN_CASES:
        ok, err = check_unguarded_tool_execution(agent)
        assert ok == exp_ok, f"{case_id}: ok={ok} != {exp_ok} err={err}"
        if not exp_ok:
            assert err is not None and err.get("code") == exp_code
        else:
            assert err is None
        results.append(True)
        print(f"[AC-1] {case_id}_PASS")
    assert all(results) and len(results) == 6


@pytest.mark.req("AC-1")
@pytest.mark.req("FR-CHECK-3")
def test_ac1_context_leakage_6cases_roundtrip() -> None:
    """词法上下文泄漏不变量：4 反例 ERR_CONTEXT_LEAKAGE + 2 正例 PASS（含反误杀）。"""
    results: list[bool] = []
    for case_id, agent, exp_ok, exp_code in CL_CASES:
        ok, err = check_context_leakage(agent)
        assert ok == exp_ok, f"{case_id}: ok={ok} != {exp_ok} err={err}"
        if not exp_ok:
            assert err is not None and err.get("code") == exp_code
        else:
            assert err is None
        results.append(True)
        print(f"[AC-1] {case_id}_PASS")
    assert all(results) and len(results) == 6
