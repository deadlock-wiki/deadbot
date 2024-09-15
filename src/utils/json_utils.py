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

def clean_dict(dict):
    """Applies a series of cleaning operations to a dictionary"""
    return sort_dict(round_dict(dict))

def sort_dict(dict):
    """Sorts a dictionary by its keys"""
    keys = list(dict.keys())
    keys.sort()
    return {key: dict[key] for key in keys}

def round_dict(dict):
    """Round all numerical values in a dictionary to varying precision"""
    """
    Values less than 1 are rounded to 3 decimal places
    Values less than 10 are rounded to 2 decimal places
    Values less than 100 are rounded to 1 decimal places
    Values less than 1000 are rounded to 0 decimal place
    """

    # Technically doesn't require a map, but easier to read this way
    rounding_map = {
        1: 3,
        10: 2,
        100: 1,
        1000: 0,
    }

    for key, value in dict.items():
        if type(value) is dict:
            dict[key] = round_dict(value)
        elif type(value) is float:

            # Round
            abs_value = abs(value)
            for threshold, precision in rounding_map.items():
                if abs_value < threshold:
                    dict[key] = round(abs_value, precision)
                    break

            # If very near to an integer, convert to integer
            precision = 1e-9
            if abs(value - int(value)) < precision:
                dict[key] = int(value)

    return dict




def is_json_serializable(obj):
    """Check if an object is JSON serializable"""
    try:
        json.dumps(obj)
        return True
    except:
        return False
