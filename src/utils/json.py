import json
from pathlib import Path

def read(path):
    with open(path) as f:
        return json.load(f)


def write(path, data):
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as outfile:
        json.dump(data, outfile, indent=4 )
