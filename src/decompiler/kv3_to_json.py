import keyvalues3 as kv3

from utils import json_utils


# Recursively accesses all nested objects and hosts json-serializable values in the returned dict
def kv3_to_dict(kv3_obj):
    # Include all items that are dicts
    dict = {}

    # If cannot access attributes, end recursion
    try:
        items = kv3_obj.items()
    except AttributeError:
        return None

    for key, value in items:
        # Only include values that are json serializable
        if not json_utils.is_json_serializable(value):
            try:
                value = kv3_to_dict(value)
                if value is None:
                    continue  # Continue to next value if its not serializable
            except TypeError:
                return None

        dict[key] = value

    return dict


# Converts kv3 object to dict, then writes dict to json
def kv3_to_json(kv3_obj, output_file):
    # output_file should always end in .json
    if not output_file.endswith('.json'):
        raise ValueError('output_file must end in .json')

    return json_utils.write(output_file, kv3_to_dict(kv3_obj))


# Removes subclass features from kv3 file and writes to json
def remove_subclass(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Fix the non-standard "subclass:" syntax by simply removing it.
    content = content.replace('subclass:', '')
    
    # 2. Fix the data corruption bug by replacing the problematic empty resource 
    #    with a standard empty string before the parser sees it.
    content = content.replace('resource_name:""', '""')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# remove subclass and write to json file
def process_file(path, out_path):
    remove_subclass(path)
    data = kv3.read(path)
    kv3_to_json(data, out_path)
