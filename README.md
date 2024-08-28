# <img src="assets/Bebop_card.png" width="36">  DeadBot 
DeadBot is an automation tool for maintaining the Deadlock Wiki - https://deadlocked.wiki/

## Guide
For use of the raw data itself, all can be found in `output-data` directory, including json and csv formats

## Development

### Setup
- `pip install poetry`
- `python -m poetry install`
- `python -m pre_commit install`
- Download Decompiler.exe from https://github.com/ValveResourceFormat/ValveResourceFormat/releases
- Extract decompiler into `Downloads/` folder
- Ensure the path to Deadlock files are correct in `src/parser/decompile.sh`

### Usage
`bash main.sh` to run end-to-end decompilation, parsing and bot (WIP)
`bash parser.sh` to just run the parser. Must have already run `main.sh` once to decompile the source files
