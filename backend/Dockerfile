FROM python:3.12-slim

RUN pip install --no-cache-dir uv

# Build context is the repo root (see docker-compose.yml).
WORKDIR /srv/backend
ENV PYTHONPATH=/srv \
    UV_NO_SYNC=1

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ /srv/backend/
COPY automation/ /srv/automation/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
