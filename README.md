# <img src="assets/Bebop_card.png" width="36">  DeadBot 
DeadBot is an automation tool for maintaining the Deadlock Wiki - https://deadlocked.wiki/

## Setup
- `pip install poetry`
- `python -m poetry install`
- `python -m pre_commit install`
- Download Decompiler.exe from https://github.com/ValveResourceFormat/ValveResourceFormat/releases
- Extract decompiler into `Downloads/` folder
- Ensure the path to Deadlock files are correct in `src/parser/decompile.sh`

## Usage
`bash main.sh`
