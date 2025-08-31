FROM python:3.11-slim
RUN apt update && apt upgrade -y && apt install -y wget unzip libicu-dev binutils

WORKDIR /tools

ENV POETRY_VER="1.8.3"
RUN python3 -m pip install poetry==$POETRY_VER
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=0 \
    POETRY_VIRTUALENVS_CREATE=False \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /repo

# Install build dependencies first
COPY pyproject.toml poetry.lock ./
RUN python3 -m poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Now install deadbot
COPY . .
RUN python3 -m poetry install

ENV BUCKET='deadlock-game-files'

# directory config
ENV DEADLOCK_DIR="/data"
ENV WORK_DIR="/work"
ENV INPUT_DIR="/input"
ENV OUTPUT_DIR="/output"

ENTRYPOINT [ "python3", "src/deadbot.py" ]
