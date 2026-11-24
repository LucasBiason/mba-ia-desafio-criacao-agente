FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_NO_PROGRESS=1 UV_PROJECT_ENVIRONMENT=/opt/aurora
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.7
COPY pyproject.toml uv.lock ./
COPY infra/packages/microservice-toolkit ./infra/packages/microservice-toolkit
COPY infra/packages/aurora-toolkit ./infra/packages/aurora-toolkit
RUN uv sync --frozen --no-dev --no-install-project
COPY services ./services
COPY --chmod=755 services/visits/entrypoint.sh /entrypoint.sh
RUN useradd --uid 10001 --no-create-home aurora
ENV PATH="/opt/aurora/bin:$PATH" APP_MODULE=services.visits.main:app
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["prod"]

FROM base AS development
RUN uv pip install --python /opt/aurora/bin/python pytest==8.4.2
USER 10001
CMD ["dev"]

FROM base AS production
USER 10001
