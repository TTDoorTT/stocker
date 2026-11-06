FROM python:3.13.11-slim@sha256:2b9c9803c6a287cafa0a8c917211dddd23dcd2016f049690ee5219f5d3f1636e
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/backend
COPY backend/requirements.lock backend/requirements-history.lock ./
RUN pip install --no-cache-dir -r requirements.lock -r requirements-history.lock
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/tests ./tests
COPY fixtures /workspace/fixtures
RUN pip install --no-cache-dir --no-deps -e .
EXPOSE 8000
