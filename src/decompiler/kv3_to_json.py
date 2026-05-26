import keyvalues3 as kv3

from utils import json_utils


# Recursively converts any object from the kv3 library into a standard, JSON-serializable Python object.
def kv3_to_dict(kv3_obj):
    # Return basic types (str, int, float, bool, None) as-is.
    if isinstance(kv3_obj, (str, int, float, bool)) or kv3_obj is None:
        return kv3_obj

    # If the object is a list, recursively convert each item.
    if isinstance(kv3_obj, list):
        return [kv3_to_dict(item) for item in kv3_obj]

    # If the object is dict-like (has .items()), recursively convert its values.
    try:
        return {k: kv3_to_dict(v) for k, v in kv3_obj.items()}
    except AttributeError:
        pass

    # Handle special Valve types like 'resource_name:' by unwrapping the 'flagged_value' object.
    if kv3_obj.__class__.__name__ == 'flagged_value' and hasattr(kv3_obj, 'value'):
        return kv3_to_dict(kv3_obj.value)

    # As a fallback, convert any other unknown object type to its string representation.
    return str(kv3_obj)


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
