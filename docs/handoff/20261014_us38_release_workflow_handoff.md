# US-38 交底：Release 工作流结构核对

> 基线：25f0a29 · 日期：2026-10-14
> 判据：Release 工作流绿

---

## 1. 结论

CI 真绿要 CI 跑。本轮做**本地结构核对**。
**未验证**：GitHub Actions 实际跑绿。

---

## 2. 本地核对（实测）

| 项 | 判据 |
|---|---|
| 6 个 job 齐 | build-windows / build-linux / create-release / docker-publish / publish-pypi / publish-testpypi |
| OIDC | permissions.id-token == write |
| 发布门控 | publish-pypi 受 vars.PUBLISH_PYPI 门控 |
| TestPyPI | 用官方 action，指向 test.pypi.org |

---

## 3. 发现（名与值不一致）

workflow 的 step 名写「repository-url 严格无尾斜杠」。
值是 https://test.pypi.org/legacy/（**带**尾斜杠）。
官方 action 的文档值就带尾斜杠。**行为正确，名字误导。**
未改 workflow（无 CI 可验，改动风险大于收益）。

---

## 4. 交付

| 文件 | 作用 |
|---|---|
| tests/test_release_workflow.py | 4 条结构核对 |

---

## 5. 未做

- 未跑 CI。真绿 = **待验证**。
