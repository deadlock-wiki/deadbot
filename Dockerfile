FROM python:3.11-slim

RUN apt update && \
    apt install -y --no-install-recommends wget unzip libicu-dev binutils git dos2unix && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tools

ENV POETRY_VER="1.8.3" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=0 \
    POETRY_VIRTUALENVS_CREATE=False \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry==$POETRY_VER

ENV DEPOT_DOWNLOADER_VER="3.4.0"
RUN wget https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_$DEPOT_DOWNLOADER_VER/DepotDownloader-linux-x64.zip \
    && unzip DepotDownloader-linux-x64.zip \
    && rm DepotDownloader-linux-x64.zip \
    && chmod +x DepotDownloader
ENV DEPOT_DOWNLOADER_CMD="/tools/DepotDownloader"

WORKDIR /repo

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY . .
RUN dos2unix /repo/src/steam/steam_db_download_deadlock.sh && \
    chmod +x /repo/src/steam/steam_db_download_deadlock.sh

ENV DEADLOCK_DIR="/data" \
    WORK_DIR="/work" \
    INPUT_DIR="/input" \
    OUTPUT_DIR="/output"

ENTRYPOINT [ "python3", "src/deadbot.py" ]
