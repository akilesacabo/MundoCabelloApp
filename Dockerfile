FROM python:3.12-slim AS builder

WORKDIR /workspace/backend
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

COPY backend/requirements/ requirements/
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install -r requirements/prod.txt

FROM python:3.12-slim AS runtime

WORKDIR /workspace/backend
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /opt/venv /opt/venv
COPY backend/src/ src/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini .
COPY app/ /workspace/app/
COPY mockups/data.json /workspace/mockups/data.json

RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m src.seed && gunicorn src.main:app -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:${PORT:-8000}"]
