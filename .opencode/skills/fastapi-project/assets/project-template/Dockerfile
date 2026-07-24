# ---- build stage: install deps into a venv ----
FROM python:3.12-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements/ requirements/
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements/prod.txt

# ---- runtime stage: copy only what's needed ----
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=builder /opt/venv /opt/venv
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
RUN useradd -m appuser
USER appuser
EXPOSE 8000
# One worker per container; scale out with replicas behind a load balancer.
CMD ["gunicorn", "src.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000"]
