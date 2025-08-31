# <img src="assets/Bebop_card.png" width="36">  DeadBot 
DeadBot is an Open Source automation tool for aggregating data from the raw game files with the purpose of accurately maintaining the Deadlock Wiki - https://deadlock.wiki/

## Guide
All output data can be found in the [deadlock-data](https://github.com/deadlock-wiki/deadlock-data) repository, which includes numeric game data and all patch changelogs

### Google Sheets 
Some data has been processed and formatted for google sheets:\
[Item Data](https://docs.google.com/spreadsheets/d/1p_uRmHc-XDJGBQeSbilOlMRboepZP5GMTsaFcFf--1c/edit?usp=sharing)

## Installation

### Setup 
1. Install Python 3.11+
2. **[OPTIONAL]** Add Python scripts dir to your environment. This lets you omit `python -m` when calling third-party modules
    - Get <python_path> with `python -m site --user-base`
    - Add to ~/.bash_profile - `export PATH="$PATH:<python_path>/Python311/Scripts"`

3. `python3 -m pip install poetry`
4. `python3 -m poetry install`
5. `python3 -m pre_commit install`
8. Setup environment variables in`.env` using `.env.example` as an example
    - **[OPTIONAL]** Clone [deadlock-data](https://github.com/deadlock-wiki/deadlock-data) repo and set `$OUTPUT_DIR` to `deadlock-data/data/current` directory to allow for easier diff viewing

### Usage

Run with `poetry run deadbot`

* `bash main.sh` to run end-to-end decompilation and perform optional cleanup. Runs based on env vars.

<details>

<summary>`poetry run deadbot -h`</summary>

```sh
usage: DeadBot [-h] [-i DL_PATH] [-w WORKDIR] [-n INPUTDIR] [-o OUTPUT] [--build_num BUILD_NUM] [-v] [-d] [-p] [-u] [-c] [--force]

Bot that lives to serve deadlock.wiki

options:
  -h, --help            show this help message and exit

path configs:
  -i DL_PATH, --dl_path DL_PATH
                        Path to Deadlock game files (also set with DEADLOCK_DIR environment variable)
  -w WORKDIR, --workdir WORKDIR
                        Directory for temp working files (also set with WORK_DIR environment variable)
  -n INPUTDIR, --inputdir INPUTDIR
                        Input directory for changelogs and wiki pages (also set with OUTPUT_DIR env variable)
  -o OUTPUT, --output OUTPUT
                        Output directory (also set with OUTPUT_DIR environment variable)
  --build_num BUILD_NUM
                        Build number of the game files to be used. Defaults to current build
  -v, --verbose         Print verbose output for extensive logging

bot actions:
  -d, --decompile       Decompiles Deadlock game files. (also set with DECOMPILE environment variable)
  -p, --parse           Parses decompiled game files into json and csv (overrides PARSE env variable)
  -u, --wiki_upload     Upload parsed data to the Wiki (also set with WIKI_UPLOAD environment variable)
  -c, --changelogs      Fetch/parse forum and local changelogs. (also set with CHANGELOGS env variable)
  --force               Forces decompilation even if game files and workdir versions match

Process Deadlock game files and extract data and stats
```

</details>

Run configured through env vars:

```sh
source .env
python3 src/deadbot.py
# or
python3 src/deadbot.py -dp
# or
python3 src/deadbot.py --decompile --parse
```

Decompile:

```sh
DL_PATH=...
OUTPUT=...
WORK_DIR=...
OUTPUT=...
python3 src/deadbot.py -d
# or
python3 src/deadbot.py -i $DL_PATH -w $WORKDIR -o $OUTPUT -d
```

Parse:

```sh
DL_PATH=...
OUTPUT=...
WORK_DIR=...
OUTPUT=...
python3 src/deadbot.py -p
# or
python3 src/deadbot.py -i $DL_PATH -w $WORKDIR -o $OUTPUT -p
```

## Docker

```sh
docker run \
  -v "$DEADLOCK_DIR":/data
  -v ./output-data:/output \
  ghcr.io/deadlock_wiki/deadbot:latest
```

Build image with `docker-compose build`

Run with `docker-compose up`

Be sure to setup volumes:

```yml
service:
    deadbot:
        ...
        volumes:
        # mount game files
        - "C:\Program Files (x86)\Steam\steamapps\common\Deadlock:/data"
          # or
        - "/mnt/SteamLibrary/steamapps/common/Deadlock:/data"
        # and an output dir
        - "./output-data:/output"
```

## Contributing
DeadBot is currently early in its development and welcomes new contributors to get involved no matter what level experience you have.

Regularly discussed in the wiki channel on [The Deadlock Wiki discord server](https://discord.com/invite/3FJpr53dfu). Ask for access on there if you are interested in contributing.

At the moment the work is fairly ad-hoc, so find me on discord as "HariyoSaag" if you're not sure where to start.
