#!/usr/bin/env bash
# 提交门禁（US-35 / 主计划 P0-2）：测试 + ruff + 判据。
#
# 为什么存在：本项目已发生两次「带红提交」。门禁把「提交前必须全绿」从人记变成机器拦。
#
# 与 CI 同源：
#   - pytest 路径取自唯一真源 tools/test_paths.txt（经 tools/verify_local.sh）
#   - Racket 用 CI 同款命令：raco test compiler/tests/
#   - ruff 路径与 CI 的 lint job 同
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# racket 可能只在仓库内 .racket/bin（minimal 发行版）
if ! command -v racket >/dev/null 2>&1; then
  if [ -x "$ROOT/.racket/bin/racket" ]; then
    export PATH="$ROOT/.racket/bin:$PATH"
  else
    echo "[gate] 找不到 racket。装 Racket 后重试（见 README）。" >&2
    exit 2
  fi
fi

if ! command -v raco >/dev/null 2>&1; then
  echo "[gate] 找不到 raco。装 compiler-lib 后重试。" >&2
  exit 2
fi

echo "[gate 1/3] Racket 编译器测试：raco test compiler/tests/"
raco test compiler/tests/

echo "[gate 2/3] ruff check + format（路径与 CI lint job 同）"
RUFF="${RUFF:-ruff}"
if ! command -v "$RUFF" >/dev/null 2>&1; then
  echo "[gate] 找不到 ruff。" >&2
  exit 2
fi
"$RUFF" check runtime host python/agentlisp_runtime runtime/tests python/tests tests scripts conftest.py
"$RUFF" format --check runtime host python/agentlisp_runtime runtime/tests python/tests tests scripts conftest.py

echo "[gate 3/3] pytest（路径来自 tools/test_paths.txt，与 CI 同源）"
tools/verify_local.sh -q --no-cov

echo "[gate] 全过。"
