# 契约口径确认记录（21 份）

> 确认人：用户代表。确认日期：2026-10-14。
> 依据：[machine-verification-report.md](../plans/machine-verification-report.md) 的机器校验 + [contracts-drafts-4-kinds.md](contracts-drafts-4-kinds.md) 的 21 个待判项。
> 基线：`41dbcff`

---

## 0. 确认结果总览

| 结论 | 份数 | 含义 |
|---|---|---|
| 通过 | 9 | 契约 = 意图。无动作 |
| 改契约 | 4 | 补可观测断言。语义由 handler 方法签名钉死 |
| 改实现 | 6 | 契约对，引擎未消费。进 P2 接线 |
| 改契约 + 改实现 | 2 | 两件都做 |

**合计 21。与契约清单逐份对齐，无遗漏。**

---

## 1. 逐份结论

| kind | 引擎消费 | 期望字节 | 结论 |
|---|---|---|---|
| priority | 是 | 168 | 通过 |
| evaluator | 是 | 89 | 通过 |
| reasoning | 是 | 62 | 通过 |
| goal-setting | 是 | 175 | 通过 |
| fsm | 是 | 114 | 通过 |
| exception | 是 | 201 | 通过 |
| exploration | 是 | 198 | 通过 |
| resource-aware | 是 | 115 | 通过 |
| decomposer | 是 | 158 | 通过 |
| hitl | 是 | 67 | 改契约 |
| guardrails-safety | 是 | 77 | 改契约 |
| rag | 是 | 72 | 改契约 |
| reflect | 是 | 80 | 改契约 |
| router | 否 | 69 | 改契约 + 改实现 |
| decomposition | 否 | 86 | 改契约 + 改实现 |
| chain | 否 | 166 | 改实现 |
| parallel | 否 | 145 | 改实现 |
| planner | 否 | 135 | 改实现 |
| a2a | 否 | 229 | 改实现 |
| learning | 否 | 235 | 改实现 |
| topic-model | 否 | 224 | 改实现 |

### 1.1 通过项（9 份）

priority、evaluator、reasoning、goal-setting、fsm、exception、exploration、resource-aware、decomposer。

### 1.2 改契约项（4 份）

hitl、guardrails-safety、rag、reflect。

**共同点**：期望均 < 90 字节。缺可观测断言。语义已由 handler 方法钉死，不发明。

### 1.3 改实现项（6 份）

chain、parallel、planner、a2a、learning、topic-model。

**共同点**：期望已足够（135–235 字节）。契约对，引擎不调。

### 1.4 双修改项（2 份）

router（69 字节）、decomposition（86 字节）。

两件都缺：期望过短，且引擎不调。

---

## 2. 21 项待判的确认明细

| # | 项 | 选择 |
|---|---|---|
| 1 | guardrails-safety 三段固定 vs 自定义 | A 固定 |
| 2 | 规则来源 | A 内置 + 用户扩展 |
| 3 | 命中后行为 | A 拒绝并留痕 |
| 4 | 三段全未命中 | A 放行不记事件 |
| 5 | a2a 传输 | A 测试 + B 生产 |
| 6 | a2a 超时 | C 可配，默认 5 秒 |
| 7 | a2a 重试 | B 重试 1 次 |
| 8 | a2a 握手取值 | A pending / connected / failed |
| 9 | a2a 对端不可达 | B 降级本地并留痕 |
| 10 | learning 写入位置 | A 产物之外 |
| 11 | learning 策略权重形态 | A 计数 |
| 12 | learning 是否用 LLM | A 不用 |
| 13 | learning 可见阈值 | A 计满 2 次 |
| 14 | topic-model 主题来源 | A 用户关键词 + 确定性打分 |
| 15 | topic-model 判定方式 | A 最高分超阈值 |
| 16 | topic-model 命中后 | B 真改路由 |
| 17 | topic-model 是否用模型 | A 不用 |
| 18 | 四份是否用 LLM | 都不用 |
| 19 | 失败留痕位置 | 现有 `events` + OTel |
| 20 | 失败行为 | 校验类拒绝；通信类降级；学习类跳过 |
| 21 | 阈值默认值标注 | 标为「经验值」 |

**来源**：用户代表 2026-10-14 回复「同意建议」+ 逐项选择。**已知**。

---

## 3. 结构结论（重要）

**本文 4 个 kind 不是新 kind。**

| 项 | 值 |
|---|---|
| 注册表 kind 总数 | 23（21 模式 + 2 语法糖） |
| 断言位置 | `tests/test_cr42_kind_coverage.py:85` |
| 本次是否改该断言 | **否**。计数不变 |
| 本次改变的是 | **引擎消费数：13 → 目标 21** |

**含义**：本次确认的 8 个 kind 全部落在既有「仅声明 8 个」名单内。
故「补行为」而非「加 kind」。枚举封闭断言不受影响。

---

## 4. 对工作项的影响

| 工作项 | 影响 |
|---|---|
| P1-1 行为槽位模型 | 无障碍。8 个 kind 将获得槽位 |
| P2-1 8 个仅声明定性 | **已定性**：全部接线，无降级 |
| P2-2 孤儿收口 | 不受影响（`memory` / `multi-agent` 未在本次 21 份内） |
| P2-4 E2E | 新增 8 条（接线后共 21 条） |
| P3-2 工作流图 | 无障碍 |
| P4-1 编排调度器 | **topic-model 项 16 依赖它** |
| P5 发布 | 无障碍 |

---

## 5. 三项待补（不阻塞契约，阻塞实现）

| # | 项 | 缺什么 | 最晚何时定 |
|---|---|---|---|
| 1 | a2a 双传输开关 | 编译期 `--transport` 还是运行期环境变量 | P2-1 之前 |
| 2 | learning 失败签名定义 | 「同签名」如何判定 | P2-1 之前 |
| 3 | topic-model 路由依赖 | 编排调度器未实现 | P4-1 之前 |

---

## 6. 未验证

1. 本文的「引擎消费」列取自 `_口径确认清单.csv` 的机器检查，未重新复跑。
2. 「通过 9 份」与用户代表初稿的「8 份」不同。差异因初稿漏计 `decomposer`。**已告知。**
3. 三项待补项的设计代价未估。
4. `guardrails-safety` 的三段若改为固定位置，是否与现行 `:hooks` 语法冲突，**我未核**。
