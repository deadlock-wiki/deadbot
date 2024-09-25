import json
import os


def read(path):
    """Read data from a JSON file to memory"""
    with open(path) as f:
        return json.load(f)


def write(path, data):
    """Write data to a JSON file"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as outfile:
        json.dump(data, outfile, indent=4)


# Remove keys from a dictionary at the specified depth
# Depth 1 removes keys from the first level of the dictionary
# Depth N removes keys from the first N levels of the dictionary
def remove_keys(data, keys_to_remove, depths_to_search=1):
    """Remove keys from the first depths_to_search levels of a dictionary"""
    if depths_to_search == 0:
        return data
    if type(data) is dict:
        data = data.copy()  # Don't alter the original data's memory
        for key in keys_to_remove:
            if key in data:
                del data[key]
        for key in data:
            # Recursive call the next depth
            data[key] = remove_keys(data[key], keys_to_remove, depths_to_search - 1)
    return data


def sort_dict(dict):
    """Sorts a dictionary by its keys"""
    keys = list(dict.keys())
    keys.sort()
    return {key: dict[key] for key in keys}


def is_json_serializable(obj):
    """Check if an object is JSON serializable"""
    try:
        json.dumps(obj)
        return True
    except Exception:
        return False
    
def compare_json_file_to_dict(json_file, dict):
    """Compare a JSON file to a dictionary"""
    return read(json_file) == dict
