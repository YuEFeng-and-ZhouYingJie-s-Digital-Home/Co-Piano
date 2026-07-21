# CoPiano v4 Backend — Dockerfile
# ──────────────────────────────────────────────
# 构建: docker build -t copiano-api .
# 运行: docker run -p 8000:8000 --env-file .env copiano-api
# ──────────────────────────────────────────────

FROM python:3.11-slim AS base

# 防止 Python 写入 .pyc,确保 stdout/stderr 不缓冲
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 系统依赖 (psycopg2 编译需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r copiano && useradd -r -g copiano copiano

WORKDIR /app

# 先装依赖,利用 Docker 缓存
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 复制应用代码
COPY . .

# 修正权限
RUN chown -R copiano:copiano /app
USER copiano

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
