FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /frontend

RUN corepack enable
RUN corepack prepare pnpm@8.15.9 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend ./
RUN pnpm build

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --retries 5 -r requirements.txt

COPY mtlogin.py app.py README.md ./
COPY --from=frontend-builder /frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8000", "--log-file", "/app/mtlogin.log", "--db-path", "/app/mtlogin.db", "--frontend-dist", "/app/frontend/dist"]
