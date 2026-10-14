# US-35 交底：提交门禁（含 Racket 依赖补齐与两处测试缺陷）

> 基线：`ec5dbf9` · 日期：2026-10-14
> 故事：US-35（作为 M，我要提交门禁，以便不再带红提交）
> 判据：注入红灯被拒

---

## 1. 结论

门禁已激活。注入红灯后 `git commit` 被拒（实测 `COMMIT_RC=1`）。

---

## 2. 交付物

| 文件 | 作用 |
|---|---|
| `.githooks/pre-commit` | 提交时调用门禁 |
| `scripts/git-gate.sh` | 门禁主体：Racket 测试 + ruff + pytest |
| `scripts/install_git_hooks.sh` | 激活 `core.hooksPath=.githooks` |
| `tests/test_commit_gate.py` | 守住门禁链路存在且同源 |

---

## 3. 门禁跑什么（与 CI 同源）

| 步 | 命令 | CI 对应 |
|---|---|---|
| 1 | `raco test compiler/tests/` | compiler-tests job |
| 2 | `ruff check` + `ruff format --check`（同 6 路径） | lint job |
| 3 | `tools/verify_local.sh -q --no-cov` | 路径取自 `tools/test_paths.txt` |

**判据 A7**：本地验证命令 == CI 命令。门禁不自己拼路径。

---

## 4. 补齐的依赖

仓库自带的 Racket 是精简发行版，缺两包。用户指示「缺就装」。

| 包 | 用途 | 装前现象 |
|---|---|---|
| `rackunit-lib` | `compiler/tests/*.rkt` | `collection not found: rackunit` |
| `compiler-lib` | `raco test` | `raco: Unrecognized command: test` |

装后：`raco test compiler/tests/` → **23 tests passed**。

---

## 5. 装依赖后发现两处测试缺陷（此前被掩盖）

装 rackunit 前，Racket 测试**未跑**。装后发现它们本来是红的。

| 缺陷 | 现象 | 修法 |
|---|---|---|
| 路径相对 cwd | 从仓库根跑，路径指到仓库外 → 全部 error | 用 `define-runtime-path`，相对源文件 |
| 退出码恒 0 | V2 用 `(void (run-tests …))`，10 个 error 也 rc=0 | 改成 `(module+ main (exit (run-tests …)))` |

**教训**：`rc=0` 不等于通过。我第一次用 rc 判断，把 10 个 error 的 V2 报成 PASS。

---

## 6. 验证（实测）

| 项 | 命令 | 结果 |
|---|---|---|
| 注入红灯 | 加一个 `assert 1 == 2`，再 `git commit` | 被拒；`COMMIT_RC=1`；pytest `1 failed, 639 passed` |
| 门禁链路 | `pytest tests/test_commit_gate.py -q --no-cov` | 5 passed |
| Racket 测试 | `raco test compiler/tests/` | 23 tests passed |
| 全仓 | `tools/verify_local.sh -q --no-cov` | 全绿 |

---

## 7. 未做

- 门禁未接入 CI。CI 是远端独立门禁，已存在。
- `git commit --no-verify` 仍可绕过。这是 git 的固有出口，不假装能堵。
- 门禁每次提交跑全量 pytest，约 3 分钟。这是「不再带红提交」的代价。
