# <img src="assets/Bebop_card.png" width="36">  DeadBot 
DeadBot is an Open Source automation tool for aggregating data from the raw game files with the purpose of accurately maintaining the Deadlock Wiki - https://deadlocked.wiki/

## Guide
All data can be found in the `output-data` directory, which includes json and csv formats

### Google Sheets
Some data has been processed and formatted for google sheets:\
[Item Data](https://docs.google.com/spreadsheets/d/1p_uRmHc-XDJGBQeSbilOlMRboepZP5GMTsaFcFf--1c/edit?usp=sharing)

## Installation

### Setup
1. Install Python 3.11+
2. **[OPTIONAL]** Add Python scripts dir to your environment. This lets you omit `python -m` when calling third-party modules
    1. Get <python_path> with `python -m site --user-base`
    2. Add to ~/.bash_profile - `export PATH="$PATH:<python_path>/Python311/Scripts"`

3. `python3 -m pip install poetry`
4. `python3 -m poetry install`
5. `python3 -m pre_commit install`
6. Download Decompiler.exe for your particular OS from https://github.com/ValveResourceFormat/ValveResourceFormat/releases 
   1. Extract decompiler into a folder and update `.env`
7. Add the paths to Deadlock files and the Decompiler in `.env` using `.env.example` as an example

### Usage

* `bash main.sh` to run end-to-end decompilation and perform optional cleanup. Runs based on env vars.

<details>

<summary>`deadbot.py -h`</summary>

```sh
usage: DeadBot [-h] [-i DL_PATH] [-w WORKDIR] [-o OUTPUT] [--decompiler_cmd DECOMPILER_CMD] [--iam_key IAM_KEY]
               [--iam_secret IAM_SECRET] [--bucket BUCKET] [-d] [-p] [-b] [-s]

Bot that lives to serve deadlocked.wiki

options:
  -h, --help            show this help message and exit

path configs:
  -i DL_PATH, --dl_path DL_PATH
                        Path to Deadlock game files (also set with DEADLOCK_PATH environment variable)
  -w WORKDIR, --workdir WORKDIR
                        Directory for temp working files (also set with WORK_DIR environment variable)
  -o OUTPUT, --output OUTPUT
                        Output directory (also set with OUTPUT_DIR environment variable)
  --decompiler_cmd DECOMPILER_CMD
                        Command for Valve Resource Format tool (also set with DECOMPILER_CMD env variable)

s3 config:
  --iam_key IAM_KEY     AWS iam key for updating bucket (overrides IAM_KEY environment variable)
  --iam_secret IAM_SECRET
                        AWS iam secret for updating bucket (overrides IAM_SECRET environment variable)
  --bucket BUCKET       S3 bucket name to push to (overrides BUCKET environment variable)

bot actions:
  -d, --decompile       Decompiles Deadlock game files. (also set with DECOMPILE environment variable)
  -p, --parse           Parses decompiled game files into json and csv (overrides PARSE env variable)
  -b, --bot_push        Push current data to wiki (also set with BOT_PUSH environment variable)
  -s, --s3_push         Push current data to s3

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
  -v "$DEADLOCK_PATH":/data
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

Regularly discussed in the wiki channel on [the Discord server](https://discord.com/invite/jUyhZKwxSW). Ask for access on there if you are interested in contributing.

At the moment the work is fairly ad-hoc, so find me on discord as "HariyoSaag" if you're not sure where to start.
