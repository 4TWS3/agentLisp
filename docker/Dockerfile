ARG PYTHON_VERSION=3.12
ARG RACKET_VERSION=8.12
ARG UV_VERSION=0.4
ARG DEBIAN_VERSION=bookworm

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM python-base AS builder-base

ARG UV_VERSION
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/root/.local/bin:/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
        libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

ADD --chmod=755 https://astral.sh/uv/${UV_VERSION}/install.sh /install-uv.sh
RUN sh /install-uv.sh

FROM python-base AS racket-base

ARG RACKET_VERSION
ARG DEBIAN_VERSION
ARG RACKET_INSTALLER="racket-minimal-${RACKET_VERSION}-x86_64-linux-${DEBIAN_VERSION}.sh"
ARG RACKET_URL="https://download.racket-lang.org/releases/${RACKET_VERSION}/installers/${RACKET_INSTALLER}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libfontconfig1 \
    && curl -fsSL "${RACKET_URL}" -o /tmp/racket-installer.sh \
    && sh /tmp/racket-installer.sh --unix-style --dest /usr/local --create-dir \
    && raco pkg install --auto --no-docs --batch \
         base \
         rackunit-lib \
         syntax/parse \
         data-lib \
         json-lib \
    && rm -rf /tmp/* /root/.cache /var/lib/apt/lists/*

FROM builder-base AS builder

WORKDIR /app

COPY python/pyproject.toml ./python/
WORKDIR /app/python
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project 2>&1 || \
    uv sync --no-dev --no-install-project

COPY python/agentlisp_runtime ./agentlisp_runtime
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev 2>&1 || \
    uv sync --no-dev

FROM python-base AS runtime-final

COPY --from=racket-base /usr/local /usr/local

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:/usr/local/bin:$PATH" \
    SCHEME_ROOT=/app/scheme \
    PYTHONPATH=/app/python

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY scheme /app/scheme
COPY python /app/python
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
COPY config /app/config

RUN chmod +x /app/docker/entrypoint.sh \
    && ln -sf /app/python/pyproject.toml /app/pyproject.toml

RUN raco pkg install --auto --no-docs --batch --link /app/scheme 2>&1 || \
    raco pkg install --auto --no-docs --batch --type dir --name agent-dsl /app/scheme

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["agentlisp", "--help"]
