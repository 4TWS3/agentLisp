#!/usr/bin/env sh
set -eu

export SCHEME_ROOT="${SCHEME_ROOT:-/app/scheme}"
export PYTHONPATH="${PYTHONPATH:-/app/python}"

if [ "${1:-}" = "sh" ] || [ "${1:-}" = "bash" ] || [ "${1:-}" = "/bin/sh" ] || [ "${1:-}" = "/bin/bash" ]; then
    exec "$@"
fi

if [ "${1:-}" = "scheme-test" ]; then
    shift
    cd "${SCHEME_ROOT}"
    exec raco test tests/ "$@"
fi

if [ "${1:-}" = "python-test" ]; then
    shift
    cd /app/python
    exec pytest tests/ "$@"
fi

if [ "${1:-}" = "repl" ]; then
    exec python -m asyncio
fi

exec "$@"
