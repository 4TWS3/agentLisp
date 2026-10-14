#!/usr/bin/env bash
# 激活 US-35 提交门禁。每个 clone 跑一次。
# 为什么用 core.hooksPath 而不是 .git/hooks：.githooks/ 可以进版本库，.git/hooks 不能。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit scripts/git-gate.sh scripts/install_git_hooks.sh
echo "core.hooksPath = $(git config core.hooksPath)"
echo "门禁已激活：git commit 会先跑 scripts/git-gate.sh"
