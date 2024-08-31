import json


def read(path):
    with open(path) as f:
        return json.load(f)


def write(path, data):
    with open(path, 'w') as outfile:
        json.dump(data, outfile, indent=4)
        
def sort_dict(dict):
    keys = list(dict.keys())
    keys.sort()
    return {key: dict[key] for key in keys}

