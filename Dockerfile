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
  PATH="$PATH:/root/.poetry/bin"

# System dependencies
RUN apt update && apt upgrade -y \
  && apt install --no-install-recommends -y \
    bash \
    build-essential \
    curl \
    # Defining build-time-only dependencies:
    $BUILD_ONLY_PACKAGES \
  && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python - \
  && poetry --version \
  # Removing build-time-only dependencies:
  && apt remove -y $BUILD_ONLY_PACKAGES \
  # Cleaning cache:
  && apt purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && apt clean -y && rm -rf /var/lib/apt/lists/*

# Create the user that will run the app
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app

# Set up permissions
RUN chmod +x run.sh \
  && chown -R appuser:appuser /app

# Copy only requirements to cache them in docker layer
COPY --chown=appuser:appuser ./poetry.lock ./pyproject.toml /app/

# Project initialization
RUN poetry install --no-dev --no-root --no-interaction --no-ansi

# Additional downloads
RUN python -c "import nltk; nltk.download('cmudict')"

COPY . /app

# Running as non-root user
USER appuser

ENTRYPOINT ["bash", "./run.sh"]
