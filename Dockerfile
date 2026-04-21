FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY mtlogin.py app.py README.md ./
COPY templates ./templates

EXPOSE 8000

CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8000", "--log-file", "/app/mtlogin.log", "--db-path", "/app/mtlogin.db"]
