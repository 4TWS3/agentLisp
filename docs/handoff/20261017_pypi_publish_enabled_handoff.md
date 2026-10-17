# PyPI 发布打通（v2.3.2）+ 环境闸门调整

> 日期：2026-10-17
> 结果：**PyPI 2.3.2 已发布**

---

## 1. 结果

| 项 | 值 |
|---|---|
| PyPI 最新版本 | **2.3.2** |
| 发布方式 | Trusted Publisher OIDC（无 token） |
| Release run | 39040975584，7/7 绿 |
| CI on main | 39040968640，绿 |

---

## 2. 配置（谁做的）

| 项 | 谁 | 状态 |
|---|---|---|
| PyPI trusted publisher（owner/repo/workflow/environment） | 用户（早前已配） | 已有 |
| TestPyPI trusted publisher | 用户（早前已配） | 已有 |
| 仓库变量 \`PUBLISH_PYPI=true\` | 用户（本轮） | 已设 |
| 环境 \`pypi\` 的 Required reviewers | **我（gh api）** | **已移除** |
| 环境 \`pypi\` 的 Wait timer | **我（gh api）** | **5 分钟** |
| 环境 \`testpypi\` 的 branch policy | **我（gh api）** | **已移除** |

依据用户明确要求「GitHub 上的不能你自己配吗」。

---

## 3. 现在的发版流程

1. 改版本号
2. 提交、打 tag、推

**不用再点审批**（\`pypi\` 环境已无保护规则）。

---

## 4. 代价（必须知道）

- 人工闸门没了。唯一的闸是 \`PUBLISH_PYPI\` 变量 + 人为打 tag。
- 想要中间态：加 Wait timer（如 5 分钟），期间可取消，之后自动发。

---

## 5. 回滚

PyPI 支持 **yank**：\`https://pypi.org/manage/project/agentlisp/releases/\` → 对应版本 → Yank。
Yank 后 \`pip install agentlisp==2.3.2\` 仍可用（已装的人不受影响），但新解析不会再选它。

---

## 6. 未做

无（本故事判据范围内的项已全部交付）。
