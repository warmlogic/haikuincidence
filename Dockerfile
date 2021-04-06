FROM python:3.9-slim-buster

ARG APP_ENV

ENV APP_ENV=${APP_ENV} \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.1.5 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_CACHE_DIR='/var/cache/pypoetry' \
  PATH="$PATH:/root/.local/bin"

# System dependencies
RUN apt-get update && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y \
    bash \
    curl \
    libpq-dev \
    # Define build-time-only dependencies
    $BUILD_ONLY_PACKAGES \
  && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python - \
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
# Can't run with --no-dev because of nltk download
RUN poetry install --no-root --no-interaction --no-ansi \
  # Clean poetry installation's cache
  && rm -rf "$POETRY_CACHE_DIR"

# Additional downloads
RUN poetry run python -c "import nltk; nltk.download('cmudict', download_dir='./nltk_data')"

COPY --chown=web:web . /app

# COPY --chown=web:web /root/nltk_data /app/nltk_data

RUN pwd
RUN ls /root
# RUN ls /root/nltk_data
RUN ls
RUN ls /app
RUN ls /app/nltk_data

# Run as non-root user
USER web

ENTRYPOINT ["poetry", "run", "python", "./app.py"]
