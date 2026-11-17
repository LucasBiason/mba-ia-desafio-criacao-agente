FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_NO_PROGRESS=1 UV_PROJECT_ENVIRONMENT=/opt/aurora
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.7
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY services ./services
RUN useradd --uid 10001 --no-create-home aurora
ENV PATH="/opt/aurora/bin:$PATH"
USER 10001
EXPOSE 8000
