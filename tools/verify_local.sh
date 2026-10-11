#!/usr/bin/env bash
# 本地验证入口：与 CI 跑**同一组路径**（唯一真源 tools/test_paths.txt）。
#
# 为什么存在：坑 #18 —— 我用「习惯的命令」（pytest tests）验，CI 用另一组路径，
# 导致「本地绿、CI 红」重复 5 次（tests/patterns 因此长期没在 CI 跑过）。
#
# 用法：
#   tools/verify_local.sh                 # 全量（无覆盖率）
#   tools/verify_local.sh -q --no-cov     # 透传任意 pytest 参数
#   PYTHON="uv run python" tools/verify_local.sh   # CI 用 uv 时
set -euo pipefail

ROOT="${BASH_SOURCE[0]}"; ROOT="$(cd "$(dirname "$ROOT")/.." && pwd)"
PATHS_FILE="$ROOT/tools/test_paths.txt"
PY="${PYTHON:-python3}"

if [ ! -f "$PATHS_FILE" ]; then
  echo "缺少唯一真源: $PATHS_FILE" >&2
  exit 2
fi

# tr -d '\r'：Windows/WSL 上文件可能是 CRLF，不去掉会让路径尾部带 \r（坑 #25）
read -r -a TEST_PATHS <<< "$(grep -v '^[[:space:]]*$' "$PATHS_FILE" | tr -d '\r' | tr '\n' ' ')"

echo "[verify_local] 路径（来自 tools/test_paths.txt）: ${TEST_PATHS[*]}"
cd "$ROOT"
exec $PY -m pytest "${TEST_PATHS[@]}" "$@"
