# syntax=docker/dockerfile:1.7
# =============================================================================
# STRATEX™ / HYDRA Core™ — Backend Multi-Stage Dockerfile
# -----------------------------------------------------------------------------
# Build targets:
#   - base-cpu   : pure-Python wheel build on slim debian (CPU/MPS deploys)
#   - base-cuda  : CUDA 12.4 runtime + cuDNN (multi-GPU deploys via
#                  nvidia-container-toolkit). Selected by build-arg HYDRA_RUNTIME.
#   - builder    : compiles wheels into /wheels for the chosen base
#   - runtime    : minimal final image — copies app + wheels, drops to non-root
# Usage:
#   CPU build:    docker build -t hydra-backend:cpu  --build-arg HYDRA_RUNTIME=cpu  ./backend
#   CUDA build:   docker build -t hydra-backend:cuda --build-arg HYDRA_RUNTIME=cuda ./backend
# =============================================================================

ARG HYDRA_RUNTIME=cpu
ARG PYTHON_VERSION=3.11

# -----------------------------------------------------------------------------
# Stage: base-cpu — Debian slim, no GPU drivers
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS base-cpu
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        git \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Stage: base-cuda — NVIDIA CUDA 12.4 runtime + cuDNN, Python installed on top
# -----------------------------------------------------------------------------
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS base-cuda
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    HYDRA_COMPUTE_DEVICE=cuda
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common \
        build-essential \
        curl \
        ca-certificates \
        git \
        libffi-dev \
        libssl-dev \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.11 \
        python3.11-dev \
        python3.11-venv \
        python3-pip \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Stage: base — resolved alias selected at build time
# -----------------------------------------------------------------------------
FROM base-${HYDRA_RUNTIME} AS base

# -----------------------------------------------------------------------------
# Stage: builder — compile wheels for all requirements
# -----------------------------------------------------------------------------
FROM base AS builder
WORKDIR /build
RUN python -m pip install --upgrade pip setuptools wheel
COPY requirements.txt ./requirements.txt
RUN python -m pip wheel \
        --wheel-dir=/wheels \
        --extra-index-url=https://d33sy5i8bnduwe.cloudfront.net/simple/ \
        -r requirements.txt

# -----------------------------------------------------------------------------
# Stage: runtime — slim final image, non-root, exposes :8001
# -----------------------------------------------------------------------------
FROM base AS runtime
ARG HYDRA_RUNTIME
ENV PYTHONPATH=/app \
    HYDRA_RUNTIME=${HYDRA_RUNTIME} \
    APP_HOME=/app \
    PORT=8001

# Non-root system user
RUN groupadd --system --gid 10001 hydra \
    && useradd --system --uid 10001 --gid hydra --create-home --home-dir /home/hydra hydra

WORKDIR ${APP_HOME}

# Install pre-built wheels (no compilers in final image)
COPY --from=builder /wheels /wheels
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy application source (.dockerignore should exclude __pycache__, tests, .env)
COPY . ${APP_HOME}/

# Filesystem hardening
RUN chown -R hydra:hydra ${APP_HOME} \
    && chmod -R u=rwX,go=rX ${APP_HOME}

USER hydra
EXPOSE 8001

# Healthcheck — hits the FastAPI /api/health if present (returns 200 fast).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --silent --fail "http://127.0.0.1:${PORT}/api/health" || exit 1

# Single-worker default — supervisor/k8s scales replicas, not workers.
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips=*"]
