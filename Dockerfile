# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production runtime or stage
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /app
COPY --from=builder /install /usr/local

COPY app.py .

EXPOSE 5000

CMD ["sh","-c", "python -c 'from app import initialize_db; initialize_db()' &&  exec gunicorn --workers 2 --bind 0.0.0.0:5000 app:app"]
