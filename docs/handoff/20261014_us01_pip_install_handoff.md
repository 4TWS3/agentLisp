# US-01 交底：pip install（P5-2 前置）

> 基线：25f0a29 · 日期：2026-10-14
> 判据：pip install agentlisp（TestPyPI）

---

## 1. 结论

本地打包 + 装 venv + 跑 CLI 自证**通过**。
**TestPyPI 上传与安装未做**（需凭据 / 网络）。

---

## 2. 实测发现（两处，已修）

| # | 发现 | 修法 |
|---|---|---|
| 1 | agentlisp2 entry point 指向 runtime.cli:app，但 runtime/cli.py **从未存在**（git 全历史无） | 删该 entry point；记 backlog B-08 |
| 2 | agentlisp --version 报 **0.1.0**（读 agentlisp-runtime 的字面量），而包是 2.3.1 | agentlisp_runtime.__version__ 改读发行版元数据（优先 agentlisp） |

---

## 3. 验证（实测）

| 项 | 结果 |
|---|---|
| 打包 | agentlisp-2.3.1-py3-none-any.whl（44 文件） |
| entry_points | 只剩 agentlisp = agentlisp_runtime.cli:app |
| venv 安装 | pip install --no-deps <whl> 成功 |
| agentlisp --version | **2.3.1** |
| C1 追认 | pyproject 哈希已更新 |

---

## 4. 未做（2026-10-17 更新：已全部消除）

- ~~TestPyPI 上传~~ → **已完成**：PyPI 2.3.2 已发布，实测可装。
- 实测（2026-10-17，隔离 venv）：
  ```
  pip install agentlisp==2.3.2      -> rc=0
  import agentlisp_runtime          -> 2.3.2
  import runtime / import host      -> OK
  agentlisp --version               -> 2.3.2
  python -m agentlisp_runtime.cli   -> 2.3.2
  ```

## 5. 原未做

- TestPyPI 上传（需凭据）。
- sdist 未验证。
