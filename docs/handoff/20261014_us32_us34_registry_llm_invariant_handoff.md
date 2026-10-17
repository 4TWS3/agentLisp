# US-32 / US-34 交底：注册表闭合 + 模式定义无 LLM 调用

> 基线：1a1c34a · 日期：2026-10-14
> 判据（US-32）：注册表数 == LANDED + 显式声明层数
> 判据（US-34）：全仓无 LLM 调用（不变式 I2）

---

## 1. 结论

两条都成机器判据。US-32 在 US-28 时已建，本轮补**显式计数**断言。
US-34 新增标准 **A13**。

---

## 2. US-32（注册表无悬空）

注册表 **23 = LANDED 13 + 声明层 8 + 非运行期 2**。

| 项 | 值 |
|---|---|
| 测试 | tests/test_cr42_registry_closed.py::test_registry_count_equals_landed_plus_declared_layers |
| 现状 | 4 passed |

---

## 3. US-34（模式定义只用声明式）

新增标准 **A13**：`runtime/patterns/` 下不得出现 `achat(` / `llm_client` /
`AnthropicClient` / `OpenAIClient`。模式 handler 必须是确定性纯函数。

| 项 | 值 |
|---|---|
| 实测 | 0 命中，通过 |
| 登记 | SRS `STD-A13`；tests/test_standards.py 期望「共 19 条」 |

---

## 4. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 注册表 | pytest tests/test_cr42_registry_closed.py | 4 passed |
| A13 | python3 tools/standards_check.py | 19 通过 / 0 失败 |
| 登记 | pytest tests/test_standards.py | 3 passed |

---

## 5. 未做

无（本故事判据范围内的项已全部交付）。
