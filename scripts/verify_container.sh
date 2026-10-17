#!/usr/bin/env bash
# US-03 验收：容器内可编译一个 .al，并运行产物里的 Agent 类。
#
# 为什么不用 docker/Dockerfile：
#   Racket 官方没有 Linux aarch64 安装包，release 镜像只有 amd64。
#   本脚本走 Debian 源的 racket（8.7），在 arm64 上原生可用。
#
# 用法：bash scripts/verify_container.sh
# 退出码：0 = 编译 + 运行都成功。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# -i 必须加：bash -s 从 stdin 读脚本，不加 -i 会读到空 stdin 直接退出（exit 0，无输出）。
docker run --rm -i -v "$ROOT:/src" -w /src python:3.12-slim-bookworm bash -s <<'INNER'
set -e

# Debian 官方 CDN（deb.debian.org）在本机不通，换 USTC 镜像。
sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' \
    /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null || true
apt-get update -qq >/dev/null 2>&1
apt-get install -y --no-install-recommends racket >/dev/null 2>&1
pip install -q pydantic pyyaml jsonschema structlog typer rich >/dev/null 2>&1

echo "arch:    $(uname -m)"
echo "racket:  $(racket --version)"

cat > /tmp/c.al <<'AL'
(define-agent c
  (:model :provider "anthropic" :name "m" :system-prompt "s")
  (:tools (import-builtin bash))
  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))
  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
            (:verify :json-schema #t)
            (:correct :max-retries 2 :on-failure abort)))
AL

racket compiler/main.rkt -i /tmp/c.al -o /tmp/c.py
echo "compile: OK ($(wc -l < /tmp/c.py) 行)"

PYTHONPATH=/src python - <<'PY'
import importlib.util
s = importlib.util.spec_from_file_location("gen", "/tmp/c.py")
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
h = m.CHarness()
print("run:     OK (harness=%s patterns=%d handlers=%d)"
      % (type(h).__name__, len(h.PATTERNS), len(h.patterns.handlers)))
PY
INNER
