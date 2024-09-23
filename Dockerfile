FROM python:3.12-slim
RUN apt update && apt upgrade -y && apt install -y wget unzip libicu-dev

# Valve Resource Format Version
# https://github.com/ValveResourceFormat/ValveResourceFormat/releases
ARG VRF_VER
ENV VRF_VER=${VRF_VER:-10.2}
ENV POETRY_VER="1.8.3"


WORKDIR /tools
RUN wget https://github.com/ValveResourceFormat/ValveResourceFormat/releases/download/$VRF_VER/Decompiler-linux-x64.zip && unzip Decompiler-linux-x64.zip

# constants
ENV DECOMPILER_PATH=/tools
RUN python3 -m pip install poetry==$POETRY_VER

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=0 \
    POETRY_VIRTUALENVS_CREATE=False \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /repo

# Install build dependencies first
COPY pyproject.toml poetry.lock ./
RUN python3 -m poetry install --no-root && rm -rf $POETRY_CACHE_DIR
#RUN python -m pre_commit install

# Now install deadbot
COPY . .
RUN python3 -m poetry install

# runtime config
ENV DECOMPILE=true
ENV PARSE=true
ENV BOT_PUSH=false
ENV BOT_WIKI_PASSWORD='hunter2'
ENV CLEANUP=true

ENV DEADLOCK_PATH="/data"
ENV OUTPUT_DIR="/output"

ENTRYPOINT [ "sh", "/repo/main.sh" ]
