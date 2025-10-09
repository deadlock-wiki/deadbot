# <img src="assets/Bebop_card.png" width="36">  Deadbot

[![Latest Release](https://img.shields.io/github/v/release/deadlock-wiki/deadbot)](https://github.com/deadlock-wiki/deadbot/releases/latest)
![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
[![Deployment](https://github.com/deadlock-wiki/deadbot/actions/workflows/deploy.yaml/badge.svg?query=branch%3Amaster)](https://github.com/deadlock-wiki/deadbot/actions/workflows/deploy.yaml?query=branch%3Amaster)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Deadbot is an open-source automation tool for extracting and processing game data for Valve's upcoming hero shooter, *Deadlock*. Its primary purpose is to accurately populate and maintain the [Deadlock Wiki](https://deadlock.wiki/).

### Key Features
*   **Data Extraction:** Downloads the latest game files by cloning the [SteamDB GameTracking-Deadlock repository](https://github.com/SteamDatabase/GameTracking-Deadlock) and using DepotDownloader for non-English localizations.
*   **Decompilation:** Processes raw game assets (`.vdata_c`, localization files) into structured JSON.
*   **Data Parsing:** Parses decompiled files to extract detailed stats for heroes, abilities, items, and NPCs.
*   **Changelog Aggregation:** Fetches official patch notes and in-game "Hero Lab" changes.
*   **Wiki Integration:** Formats data and changelogs into wikitext and uploads them directly to the Deadlock Wiki.

---

## Project Architecture

Deadbot uses a two-repository system to separate logic from data:

1.  **[deadbot (This Repository)](https://github.com/deadlock-wiki/deadbot):** Contains all the Python code for decompiling, parsing, and uploading data.
2.  **[deadlock-data](https://github.com/deadlock-wiki/deadlock-data):** Stores the JSON, CSV, localization, and changelog files produced by this tool. Keeping data in a separate repository allows for clean, version-controlled tracking of game data changes over time.

The data flow is as follows:
**SteamDB GameTracking Repo → Deadbot (Parse) → `deadlock-data` Repository → Deadlock Wiki**

---

## Getting Started

### Prerequisites
*   [Git](https://git-scm.com/)
*   [Python 3.11+](https://www.python.org/)
*   [Poetry](https://python-poetry.org/docs/#installation) (Python dependency manager)

### Usage Scenarios

#### 1. Parsing Existing Local Game Files
If you already have Deadlock installed, this is the fastest way to get the data.
```sh
# For Linux/macOS
DEADLOCK_DIR="/path/to/Steam/steamapps/common/Deadlock" poetry run deadbot --parse

# For Windows PowerShell
$env:DEADLOCK_DIR="C:\Program Files (x86)\Steam\steamapps\common\Deadlock"; poetry run deadbot --parse
```

#### 2. Downloading and Parsing Game Files
If you don't have the game files locally, Deadbot can download them for you. This is the method used by the automated workflows.
```sh
# This will clone game files into the DEADLOCK_DIR specified in your .env file
poetry run deadbot --import_files --parse
```

### Full Installation
1.  **Clone the repository:**
    ```sh
    git clone https://github.com/deadlock-wiki/deadbot.git
    cd deadbot
    ```

2.  **Install dependencies using Poetry:**
    ```sh
    poetry install
    ```

3.  **Set up pre-commit hooks (for development):**
    ```sh
    poetry run pre-commit install
    ```

4.  **Configure your environment:**
    Copy the example environment file.
    ```sh
    cp .env.example .env
    ```
    Then, edit the `.env` file with your desired paths and credentials.

    | Variable | Example Value | Required? | Description |
    | --- | --- | --- | --- |
    | `DEADLOCK_DIR` | `C:\Steam\common\Deadlock` | ✅ | Path to local game files, or destination for downloaded files. |
    | `STEAM_USERNAME` | `mySteamLogin` | ❌ (Only for downloading) | Your Steam account username. |
    | `STEAM_PASSWORD` | `mySteamPassword` | ❌ (Only for downloading) | Your Steam account password. |
    | `OUTPUT_DIR` | `../deadlock-data/data/current` | ❌ (Defaults to `./output-data`) | Where the parsed data files will be saved. |
    | `DEPOT_DOWNLOADER_CMD` | `C:\Tools\DepotDownloader.exe` | ❌ (For non-English parsing) | Path to the DepotDownloader executable. |

    For full configuration see [Parameters](#parameters)
5.  **Run the bot:**
    The simplest way to run the bot is by using `poetry run deadbot`, which will use your `.env` file for configuration.

    You can override any `.env` setting by providing command-line flags. For example, to run a full import and parse regardless of your `.env` settings:
    ```sh
    # Run a full process: download, decompile, and parse
    poetry run deadbot --import_files --decompile --parse

    # Just parse existing files
    poetry run deadbot --parse
    ```

---
## Parameters
| Section          | Argument                                      | Description                                                                                                                             | Environment Var        |
| ---------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| **General**      | `-h, --help`                                  | Show help message and exit.                                                                                                             |                        |
|                  | `-w, --workdir WORKDIR`                       | Directory for temporary working files.                                                                                                  | `WORK_DIR`             |
|                  | `-n, --inputdir INPUTDIR`                     | Input directory for changelogs and wiki pages.                                                                                          | `INPUT_DIR`            |
|                  | `-o, --output OUTPUT`                         | Output directory for generated files.                                                                                                   | `OUTPUT_DIR`           |
|                  | `--english-only`                              | Only parse English localizations.                                                                                                       | `ENGLISH_ONLY`         |
|                  | `--force`                                     | Forces decompilation even if game files and workdir versions match.                                                                     |                        |
|                  | `-v, --verbose`                               | Enable verbose logging for detailed output.                                                                                             |                        |
| **Steam Config** | `--steam_username STEAM_USERNAME`             | Steam username for downloading game files.                                                                                              | `STEAM_USERNAME`       |
|                  | `--steam_password STEAM_PASSWORD`             | Steam password for downloading game files.                                                                                              | `STEAM_PASSWORD`       |
|                  | `--depot_downloader_cmd DEPOT_DOWNLOADER_CMD` | Path to the **DepotDownloader** executable directory.                                                                                   | `DEPOT_DOWNLOADER_CMD` |
|                  | `--manifest_id MANIFEST_ID`                   | Manifest ID to download. Defaults to `latest`. Browse manifests: [SteamDB Depot 1422456](https://steamdb.info/depot/1422456/manifests/) | `MANIFEST_ID`          |
| **Bot Actions**  | `-i, --import_files`                          | Import game and localization files using DepotDownloader.                                                                               | `IMPORT_FILES`         |
|                  | `-d, --decompile`                             | Decompile Deadlock game files.                                                                                                          | `DECOMPILE`            |
|                  | `-p, --parse`                                 | Parse decompiled files into JSON and CSV.                                                                                               | `PARSE`                |
|                  | `-c, --changelogs`                            | Fetch and parse both forum and local changelogs.                                                                                        | `CHANGELOGS`           |
|                  | `-u, --wiki_upload`                           | Upload parsed data to the Wiki.                                                                                                         | `WIKI_UPLOAD`          |
|                  | `--dry_run`                                   | Run wiki upload in dry-run mode (no actual upload).                                                                                     | `DRY_RUN`              |


## Docker
You can also run Deadbot using Docker, which is how it's deployed in production.

1.  **Build the image:**
    ```sh
    docker compose build
    ```
2.  **Run the container:**
    Make sure your `.env` file is configured, as `docker-compose` will use it to set environment variables inside the container.
    ```sh
    docker compose up
    ```
    This command will build the image if it doesn't exist, then start the container and run the bot.

---

## Automation (CI/CD)
This project uses GitHub Actions to automate its workflow:
*   **Auto-Deploy:** A scheduled action checks for game updates on SteamDB every hour. If a new version is found, it automatically runs the full data pipeline and commits the updated data to the `deadlock-data` repository.
*   **Pull Request Integration:** When a PR is opened in `deadbot`, a corresponding draft PR is automatically created in `deadlock-data` to show the impact of the changes on the output files.
*   **CI Checks:** All PRs are automatically linted and tested to ensure code quality.
*   **Release Management:** Merging to `master` triggers a release workflow that builds and pushes a new Docker image and creates a GitHub release.

---

## Acknowledgements
This project relies on the excellent work of the SteamDB team for tracking and providing access to Deadlock's game files via their [GameTracking-Deadlock](https://github.com/SteamDatabase/GameTracking-Deadlock) repository.

---

## Contributing
Deadbot is in active development and welcomes new contributors! Whether you're experienced or new to coding, your help is appreciated.

*   The best place to get involved is the `#wiki-tech` channel on **[The Deadlock Wiki Discord server](https://discord.com/invite/3FJpr53dfu)**; ask for contributor access and ping `@hariyosaag` if you’re not sure where to start.

For those who prefer to jump right in, check out the **[good first issues](https://github.com/deadlock-wiki/deadbot/labels/good%20first%20issue)** to find easy ways to contribute.