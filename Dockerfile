FROM python:3.10-slim-bullseye

ARG APP_ENV

ENV APP_ENV=${APP_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.2.1 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  PATH="$PATH:/root/.local/bin"

# System dependencies
RUN apt-get update && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y \
    bash \
    # For poetry
    curl \
    # For psycopg2
    libpq-dev \
    # Define build-time-only dependencies
    $BUILD_ONLY_PACKAGES \
  && curl -sSL https://install.python-poetry.org | python3 - \
  && poetry --version \
  # Remove build-time-only dependencies
  && apt-get remove -y $BUILD_ONLY_PACKAGES \
  # Clean cache
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && apt-get clean -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set up permissions
RUN groupadd -r web && useradd -d /app -r -g web web \
  && chown -R web:web /app

# Copy only requirements to cache them in docker layer
COPY --chown=web:web ./poetry.lock ./pyproject.toml /app/

# Project initialization
RUN poetry install --without dev --no-interaction --no-ansi \
  # Clean poetry installation's cache
  && rm -rf "$POETRY_CACHE_DIR"

# Additional downloads
RUN poetry run python -c "import nltk; nltk.download('cmudict', download_dir='./nltk_data')"

COPY --chown=web:web . /app

# Run as non-root user
USER web

ENTRYPOINT ["poetry", "run", "python", "./haikuincidence/app.py"]
