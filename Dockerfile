FROM python:3.12-slim
RUN apt update && apt upgrade -y && apt install -y wget unzip libicu-dev


WORKDIR /tools
# Valve Resource Format Version https://github.com/ValveResourceFormat/ValveResourceFormat/releases
ENV VRF_VER="10.2"
# used to decompile game .vpk and .vdata_c files
RUN wget https://github.com/ValveResourceFormat/ValveResourceFormat/releases/download/$VRF_VER/Decompiler-linux-x64.zip && unzip Decompiler-linux-x64.zip
ENV DECOMPILER_CMD=/tools/Decompiler

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

# runtime config
ENV IMPORT_FILES=true
ENV DECOMPILE=false
ENV PARSE=true
ENV CHANGELOGS=true
ENV WIKI_UPLOAD=false
ENV CLEANUP=true
ENV S3_PUSH=false

ENV BUCKET='deadlock-game-files'

# directory config
ENV DEADLOCK_PATH="/data"
ENV WORK_DIR="/work"
ENV INPUT_DIR="/input"
ENV OUTPUT_DIR="/output"

ENTRYPOINT [ "python3", "src/deadbot.py" ]
