# VyaparSense API + RQ worker — one image, two commands.
#
# Build from the REPO ROOT (the build needs both packages/ml and apps/api):
#   docker build -f apps/api/Dockerfile -t vyaparsense-api .
#
# Run the API:
#   docker run -p 8000:8000 --env-file .env vyaparsense-api
# Run the worker (same image, override the command):
#   docker run --env-file .env vyaparsense-api rq worker forecasts --url "$REDIS_URL"
# Apply migrations (release/pre-deploy step):
#   docker run --env-file .env vyaparsense-api alembic upgrade head
FROM python:3.13-slim AS runtime

# libgomp1 is LightGBM's OpenMP runtime; everything else installs from wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the ML library first (it changes least → better layer caching), then
# the API. The API depends on vyaparsense-ml, which is already satisfied locally,
# so pip won't reach out to PyPI for it.
COPY packages/ml ./packages/ml
RUN pip install ./packages/ml
COPY apps/api ./apps/api
RUN pip install ./apps/api

# Drop privileges.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Run from apps/api so alembic.ini + migrations/ are on hand for the migrate step.
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
