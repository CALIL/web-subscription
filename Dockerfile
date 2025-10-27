# ビルドステージ - uv公式イメージを使用
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# 依存関係ファイルをコピー（キャッシュ効率化のため先にコピー）
COPY pyproject.toml uv.lock ./

# 依存関係をシステムにインストール
RUN uv pip sync --system --no-cache

# 実行ステージ
FROM python:3.13-slim-bookworm

WORKDIR /app

# ビルドステージから依存関係をコピー
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションコードをコピー
COPY app ./app

# Cloud Run用の環境変数
ENV PORT=8080
ENV APP_ENV=production
ENV PYTHONUNBUFFERED=1

# 非rootユーザーの作成と権限設定
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ヘルスチェックエンドポイント
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# ポート公開
EXPOSE 8080

# アプリケーション起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]