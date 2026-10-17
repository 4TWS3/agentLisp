# 上生产前的 5 个缺口：本轮闭掉 4 个 + 1 个明确降级

> 日期：2026-10-17
> 顺序按产品+架构判断：鉴权 → 槽位对齐 → Temporal 口径 → 子 Agent 真跑 → 环境 E2E

---

## 1. 结论

| # | 缺口 | 本轮结果 |
|---|---|---|
| 1 | 网关无鉴权 | **已修**：Bearer token，未配置拒绝启动 |
| 2 | 槽位模型与实际不一致 | **已修**：5 个编排 kind 落地，口径 21/18/3 |
| 3 | Temporal 是骨架 | **已明确降级**：WARNING + DirectRunner，专用错误类型 |
| 4 | 子 Agent 不真跑 | **已修**：spawn 真跑 1 个，fanout 真并发 N 个 |
| 5 | infra/真模型 E2E 从未跑绿 | **已验证**：infra 3 条 + 真模型 1 条 |

---

## 2. 逐项证据

### 2.1 网关鉴权

- `host/gateway_sse.py`：新增 `GatewayAuthNotConfiguredError` + `resolve_gateway_token()` + HTTP 中间件。
- 行为：`/v1/*` 要求 `Authorization: Bearer $AGENTLISP_GATEWAY_TOKEN`；`/health` 与文档开放。
- 未配 token 且未显式放行 → **拒绝启动**（不给「忘了配」留空子）。
- 本机开发：`AGENTLISP_GATEWAY_ALLOW_ANONYMOUS=1`，且打 WARNING。
- 测试：`host/tests/test_gateway_auth.py` 3 条。

### 2.2 槽位模型对齐

- `SLOTS` 新增 `orchestrate` 调用点证据（`orchestrator.select_next(`）。
- `KIND_SLOTS`：chain / planner / router / parallel / decomposition → `["orchestrate"]`。
- 口径短语：**契约 21 / 落地 18 / 声明层 3**（README / 注释 / 落地清单三处同步）。
- 5 份契约文档的槽位行改为 `orchestrate`。

### 2.3 Temporal 口径

- `TemporalRunner.submit/wait` 抛 `DurableExecutionUnavailableError`，消息写明「进程重启会丢」。
- `default_runner(prefer_temporal=True)`：WARNING + 退回 DirectRunner（降级但留痕）。
- 测试：`host/tests/test_temporal_explicit_degrade.py` 2 条。

### 2.4 子 Agent 真执行

- `BaseHarnessV2._run_subagent`：同配置/同 LLM/同工具，**独立实例**（scoped_worker 是栈式切换，并发会互踩）。
- `_run_orchestrated_children`：spawn 跑 1 个；fanout 用 `asyncio.gather` 真并发。
- 子 Agent 失败不拖垮父级，但打 WARNING。
- 测试：`tests/test_orchestrator_real_subagents.py` 2 条。

### 2.5 环境 E2E

| 命令 | 结果 |
|---|---|
| `AGENTLISP_DOCKER_INFRA=true pytest host/tests/test_infra_docker_e2e.py` | **3 passed** |
| `AGENTLISP_REAL_ENV=1 pytest tests/test_us29_real_env.py` | **1 passed**（Ollama qwen3） |

前提：redis / jaeger / temporal 三个容器在跑；Ollama 在跑。

---

## 3. 仍未做

| 项 | 状态 |
|---|---|
| Temporal 真实现 | 未做（本轮只把「不可用」说清） |
| 网关限流/配额 | 未做 |
| 真实 OpenAI/Anthropic 端点验收 | 未做（只验了 Ollama） |
| release 镜像 arm64 | 未做 |
| B-02/B-05/B-07 | 未做 |
