# US-46 交底：:evolution 契约运行时消费点（P2-3 / P6-4）

> 基线：`0367df4` · 日期：2026-10-14
> 故事：US-46（作为 A，我要 `:evolution` 契约可读，以便不空转）
> 判据：运行时有可观测点读取 `EVOLUTION`

---

## 1. 结论

`BaseHarnessV2.__init__` 读 `self.EVOLUTION`，校验形状，暴露为 `harness.evolution`，并留日志。
消费点从「全仓零引用」变为「有读取 + 有断言」。

---

## 2. 之前的状态

产物写 `self.EVOLUTION`（emitter 的 `emit-evolution-dict`），但运行时零引用（机器验证报告 §5 实测）。
契约存在但无人读 = **空转**。

---

## 3. 实现

| 文件 | 改动 |
|---|---|
| `runtime/base_harness_v2.py` | `__init__` 末尾 `self.evolution = self._load_evolution_contract()`；新增该方法 |
| `tests/test_evolution_consumption.py` | 2 条：带块 → dict + targets；无块 → None |

**形状校验**：必须是 dict，且含 `mutation_targets` / `immutable_invariants` / `verifier_gate`。
缺键即抛，不静默。

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 消费点 | `pytest tests/test_evolution_consumption.py -q --no-cov` | 2 passed |
| evolution 回归 | `pytest tests/test_cr42_evolution.py -q --no-cov` | 8 passed |
| 判据 | `python3 tools/standards_check.py` | 18 通过 / 0 失败 |

---

## 5. 未做

- 未写离线 Evolver（RSI P7-2）。本故事只做「契约被读」。
- `EVOLUTION` 未进 trace / CLI 输出。当前可观测点是 `harness.evolution` + 日志。
