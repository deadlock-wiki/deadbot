FROM python:3.11-slim
RUN apt update && apt upgrade -y && apt install -y wget unzip libicu-dev binutils

# git is needed for downloading game data from SteamDB repo
RUN apt install -y --no-install-recommends git

WORKDIR /tools

ENV POETRY_VER="1.8.3"
RUN python3 -m pip install poetry==$POETRY_VER
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=0 \
    POETRY_VIRTUALENVS_CREATE=False \
    POETRY_CACHE_DIR=/tmp/poetry_cache

ENV DEPOT_DOWNLOADER_VER="3.4.0"
RUN wget https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_$DEPOT_DOWNLOADER_VER/DepotDownloader-linux-x64.zip \
    && unzip DepotDownloader-linux-x64.zip \
    && rm DepotDownloader-linux-x64.zip \
    && chmod +x DepotDownloader
ENV DEPOT_DOWNLOADER_CMD="/tools/DepotDownloader"

WORKDIR /repo

# Install build dependencies first
COPY pyproject.toml poetry.lock ./
RUN python3 -m poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Now install deadbot
COPY . .
RUN python3 -m poetry install
RUN apt-get install -y dos2unix && dos2unix /repo/src/steam/steam_db_download_deadlock.sh

RUN chmod +x /repo/src/steam/steam_db_download_deadlock.sh

# directory config
ENV DEADLOCK_DIR="/data"
ENV WORK_DIR="/work"
ENV INPUT_DIR="/input"
ENV OUTPUT_DIR="/output"

ENTRYPOINT [ "python3", "src/deadbot.py" ]
