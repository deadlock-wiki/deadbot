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
ENV DECOMPILE=true
ENV PARSE=true
ENV BOT_PUSH=false
ENV CLEANUP=true

# credentials
ENV IAM_KEY=$IAM_KEY
ENV IAM_SECRET=$IAM_SECRET

ENV BOT_WIKI_USER=$BOT_WIKI_USER
ENV BOT_WIKI_PASS=$BOT_WIKI_PASS

# directory config
ENV USE_LOCAL_FILES=$USE_LOCAL_FILES
ENV DEADLOCK_PATH="/data"
ENV WORK_DIR="/work"
ENV OUTPUT_DIR="/output"

ENTRYPOINT [ "sh", "/repo/main.sh" ]
