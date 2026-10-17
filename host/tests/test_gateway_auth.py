"""P0-1：网关必须鉴权。

判据：
  - 未配 token 且未显式放行 → create_app() 抛错（不给「忘了配」留空子）
  - 配了 token → /v1/* 无 Bearer 头返回 401，带了放行
  - 显式匿名（AGENTLISP_GATEWAY_ALLOW_ANONYMOUS=1）→ 放行且打 WARNING
"""

from __future__ import annotations

import logging

import pytest

pytest.importorskip("fastapi", reason="未装可选依赖组 web")
pytest.importorskip("httpx", reason="未装 httpx")

from fastapi.testclient import TestClient

from host.gateway_sse import GatewayAuthNotConfiguredError, create_app


def test_refuses_to_start_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTLISP_GATEWAY_TOKEN", raising=False)
    monkeypatch.delenv("AGENTLISP_GATEWAY_ALLOW_ANONYMOUS", raising=False)
    with pytest.raises(GatewayAuthNotConfiguredError):
        create_app()


def test_requires_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTLISP_GATEWAY_TOKEN", "s3cret")
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    r = client.get("/v1/runs/nope")
    assert r.status_code == 401, r.text
    r2 = client.get("/v1/runs/nope", headers={"Authorization": "Bearer s3cret"})
    assert r2.status_code != 401, r2.text


def test_anonymous_mode_is_explicit_and_loud(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    monkeypatch.delenv("AGENTLISP_GATEWAY_TOKEN", raising=False)
    monkeypatch.setenv("AGENTLISP_GATEWAY_ALLOW_ANONYMOUS", "1")
    with caplog.at_level(logging.WARNING):
        app = create_app()
    assert any("AGENTLISP_GATEWAY_TOKEN" in rec.message for rec in caplog.records), "必须留痕"
    assert TestClient(app).get("/v1/runs/nope").status_code != 401
