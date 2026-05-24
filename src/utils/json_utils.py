import json
import os

from utils import num_utils


class CaseInsensitiveDict(dict):
    """A dict that looks up string keys case-insensitively while preserving
    the original key casing for iteration, JSON serialization, etc.

    Designed to absorb inconsistent capitalization that occasionally appears
    in Valve's data files (e.g. ``m_strVAlue`` vs ``m_strValue``,
    ``AbilitYCharges`` vs ``AbilityCharges``).

    Semantics:
      - ``d[key]``, ``d.get(key)``, ``key in d`` all compare keys via
        ``key.lower()``. The first stored casing of a key wins; subsequent
        writes with a different casing replace the value but keep the
        original key string. Non-string keys are stored exactly as-is.
      - The dict still serializes / iterates with the original keys, so
        downstream consumers see PascalCase or whatever casing the source
        used.

    Use ``wrap_case_insensitive`` to recursively convert a parsed JSON tree.
    """

    def __init__(self, data=None, **kwargs):
        super().__init__()
        # lowercased str key -> the canonical str key currently stored
        self._ci_index: dict[str, str] = {}
        if data is not None:
            self.update(data)
        if kwargs:
            self.update(kwargs)

    def __setitem__(self, key, value):
        if isinstance(key, str):
            lower = key.lower()
            existing = self._ci_index.get(lower)
            if existing is not None and existing != key:
                # collision: drop the prior case-variant so only one stays
                dict.__delitem__(self, existing)
            self._ci_index[lower] = key
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        if isinstance(key, str):
            actual = self._ci_index.get(key.lower())
            if actual is None:
                raise KeyError(key)
            return dict.__getitem__(self, actual)
        return dict.__getitem__(self, key)

    def __delitem__(self, key):
        if isinstance(key, str):
            actual = self._ci_index.pop(key.lower(), None)
            if actual is None:
                raise KeyError(key)
            dict.__delitem__(self, actual)
            return
        dict.__delitem__(self, key)

    def __contains__(self, key):
        if isinstance(key, str):
            return key.lower() in self._ci_index
        return dict.__contains__(self, key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, *args):
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            raise
        del self[key]
        return value

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return default

    def update(self, other=None, **kwargs):
        if other is not None:
            if hasattr(other, 'items'):
                for k, v in other.items():
                    self[k] = v
            else:
                for k, v in other:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def copy(self):
        new = CaseInsensitiveDict()
        for k, v in self.items():
            new[k] = v
        return new


def wrap_case_insensitive(obj):
    """Recursively wrap dict-trees in CaseInsensitiveDict."""
    if isinstance(obj, dict):
        wrapped = CaseInsensitiveDict()
        for k, v in obj.items():
            wrapped[k] = wrap_case_insensitive(v)
        return wrapped
    if isinstance(obj, list):
        return [wrap_case_insensitive(item) for item in obj]
    return obj


def read(path, ignore_error=False):
    """
    Read data from a JSON file to memory.
    Args:
        path (str): The path to the JSON file.
        ignore_error (bool, optional): If true, return None instead of throwing an error (eg. file not found).
    Returns:
        dict: The data from the JSON file.
    """
    try:
        # Explicitly specify encoding='utf-8' to handle non-ASCII characters correctly
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        if ignore_error:
            return None
        raise e


def write(path, data):
    """
    Write data to a JSON file.
    Args:
        path (str): The path to the JSON file.
        data (dict): The data to write to the JSON file.
    """
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
    if isinstance(data, dict):
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
                    # If the value is a list, check the structure
                    # of each element that are dictionaries
                    for i, elem in enumerate(datas1[key]):
                        if isinstance(elem, dict):
                            more_invalid_keys = validate_structures(elem, datas2[key][i], elem.keys())
                            if len(more_invalid_keys) > 0:
                                invalid_keys[key] = more_invalid_keys

    return invalid_keys


def strip_zeroes(obj: dict):
    output = obj.copy()
    for key, value in obj.items():
        if num_utils.is_zero(value):
            output.pop(key)

    return output


def deep_get(data, *keys):
    """Safely access nested dictionary keys."""
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data


def read_value(data, *keys):
    """Safely access nested dictionary keys and convert to number if possible."""
    value = deep_get(data, *keys)
    return num_utils.assert_number(value)
