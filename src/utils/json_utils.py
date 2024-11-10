import json
import os


def read(path):
    """Read data from a JSON file to memory"""
    # Explicitly specify encoding='utf-8' to handle non-ASCII characters correctly
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write(path, data):
    """Write data to a JSON file"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Use encoding='utf-8' to prevent Unicode characters from being escaped
    with open(path, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, indent=4, ensure_ascii=False)


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
    try:
        return read(json_file) == dict
    except Exception:
        return False
    
def validate_structures(datas1, datas2, structure_keys_to_validate):
    """
    Validate that the structure (meaning shape and keys, but not value)
    of the values for each key in datas1 and datas2 match

    Returns a hash of all the invalid keys

    In consecutive layers, the keys of datas1 are displayed for the invalid keys
    """
    invalid_keys = dict()

    data_to_test = [[datas1, datas2], [datas2, datas1]]

    # Test both ways
    for datas1, datas2 in data_to_test:
        for key in datas1.keys():
            if key not in structure_keys_to_validate:
                continue

            # Ensure both contain the key
            value1 = datas1.get(key, None)
            value2 = datas2.get(key, None)
            if value1 is None or value2 is None:
                invalid_keys[key] = 'The key for this value is missing in one of the data sets'
                continue

            # Check if the values differ, as this must occur first
            if datas1[key] != datas2[key]:
                # Ensure the types match
                type1 = type(datas1[key])
                type2 = type(datas2[key])
                if type1 != type2:
                    invalid_keys[key] = 'The types of the values differ here'
                    continue

                # If the value is a dictionary, recursively check the structure
                if isinstance(datas1[key], dict):
                    more_invalid_keys = validate_structures(value1, value2, value1.keys())
                    if len(more_invalid_keys) > 0:
                        # Add the invalid keys to the current dict
                        invalid_keys[key] = more_invalid_keys

                elif isinstance(datas1[key], list):
                    # If the value is a list, check the structure of each element that are dictionaries
                    for i, elem in enumerate(datas1[key]):
                        if isinstance(elem, dict):
                            more_invalid_keys = validate_structures(elem, datas2[key][i], elem.keys(), more_invalid_keys)
                            if len(more_invalid_keys) > 0:
                                invalid_keys[key] = more_invalid_keys

    return invalid_keys
