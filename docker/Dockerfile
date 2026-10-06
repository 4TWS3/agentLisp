ARG PYTHON_VERSION=3.12
ARG RACKET_VERSION=8.12
ARG UV_VERSION=0.4.0
ARG DEBIAN_VERSION=bookworm

# OCI Image Specification (org.opencontainers.image.*) 标签默认值。
# 在正式发布时，GitHub Actions release.yml docker/metadata-action@v5 会通过
# build-push-action 的 --build-arg 注入真实值（基于 GITHUB_SHA / GITHUB_REPOSITORY
# / github.event.release.tag_name / {{date '...'}}）；本地 docker build 未传则回退到
# 下方占位值，保证镜像仍满足 OCI 标注契约（非空字符串 + 合法 URI/semver 形状）。
ARG OCI_SOURCE="https://github.com/4TWS3/agentLisp"
ARG OCI_VERSION="0.1.0-dev"
ARG OCI_REVISION="0000000000000000000000000000000000000000"
ARG OCI_CREATED="1970-01-01T00:00:00Z"
ARG OCI_TITLE="AgentLisp v2.0 Runtime Image"

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

FROM python-base AS builder-base

ARG UV_VERSION
ENV VIRTUAL_ENV=/app/.venv \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/root/.cargo/bin:/root/.local/bin:/app/.venv/bin:$PATH"

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
ARG RACKET_INSTALLER="racket-minimal-${RACKET_VERSION}-x86_64-linux-bc.sh"
ARG RACKET_URL="https://download.racket-lang.org/releases/${RACKET_VERSION}/installers/${RACKET_INSTALLER}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libfontconfig1 \
    && curl -fsSL "${RACKET_URL}" -o /tmp/racket-installer.sh \
    && sh /tmp/racket-installer.sh --unix-style --dest /usr/local --create-dir \
    && raco pkg install --auto --no-docs --batch \
         rackunit-lib \
         data-lib \
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

COPY --from=builder /app/python/.venv /app/.venv
COPY scheme /app/scheme
COPY python /app/python
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
COPY config /app/config

RUN chmod +x /app/docker/entrypoint.sh \
    && ln -sf /app/python/pyproject.toml /app/pyproject.toml

RUN cd /app \
    && ls scheme/ \
    && raco pkg install --auto --no-docs --batch --link ./scheme 2>&1 || \
       raco pkg install --auto --no-docs --batch --type dir --name agent-dsl ./scheme

# ===== OCI Image Format Specification 标注（ANNOTATIONS 1.0）=====
# 5 个标准键 org.opencontainers.image.{source,version,revision,created,title}
# 在 release.yml CI 中由 docker/metadata-action@v5 生成并通过 build-push-action --build-arg
# 覆盖；本地 build 未传 arg 时使用顶部 ARG 默认值，保证标签不会是空字符串违反 OCI。
ARG OCI_SOURCE
ARG OCI_VERSION
ARG OCI_REVISION
ARG OCI_CREATED
ARG OCI_TITLE
LABEL org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.version="${OCI_VERSION}" \
      org.opencontainers.image.revision="${OCI_REVISION}" \
      org.opencontainers.image.created="${OCI_CREATED}" \
      org.opencontainers.image.title="${OCI_TITLE}"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["agentlisp", "--help"]
