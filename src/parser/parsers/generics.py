import utils.json_utils as json_utils
import utils.string_utils as string_utils
import os


class GenericParser:
    """
    Lightly parse the generic data to have more readable keys.

    Validate structures used by the frontend to identify
    possible failure points in the case they are modified
    by Valve.
    """

    def __init__(self, output_dir, generic_data):
        self.OUTPUT_DIR = output_dir
        self.generic_data = generic_data

    def _read(self):
        if not os.path.exists(self.OUTPUT_DIR):
            return None

        # Read existing generic data from file
        return json_utils.read(self.OUTPUT_DIR)

    def run(self):
        # Parse generic data
        possible_prefixes = ['m_str', 'm_map', 'm_n', 'm_fl', 'm_', 'fl', 'E', 'n']
        parsed_generics = remove_prefixes(self.generic_data, possible_prefixes)

        # Read existing generic data
        existing_generics = self._read()

        # If there ie existing data, validate the structure
        if existing_generics is not None:
            structure_keys_to_validate = ['ObjectiveParams', 'RejuvParams', 'ItemPricePerTier']
            invalid_keys = validate_structures(
                existing_generics, parsed_generics, structure_keys_to_validate
            )
            
            if len(invalid_keys) > 0:
                print(
                    '*WARNING* A structure within Generic data:'
                    + f' {invalid_keys} is now different. Please verify the changes,'
                    + ' and update the frontend page [[Module:GenericData]] accordingly.'
                )

        return parsed_generics


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


def remove_prefixes(generic_data, possible_prefixes):
    """
    Recursively remove prefixes from keys in a dictionary
    """
    new = dict()
    for key, value in generic_data.items():
        # Remove prefix from the key
        for possible_prefix in possible_prefixes:
            new_key = string_utils.remove_prefix(key, possible_prefix)
            if new_key != key:
                # prefix found
                break

        # If value is a container, recursively remove prefixes
        if isinstance(value, dict):
            value = remove_prefixes(value, possible_prefixes)
        elif isinstance(value, list):
            for i, elem in enumerate(value):
                if isinstance(elem, dict):
                    value[i] = remove_prefixes(elem, possible_prefixes)

        new[new_key] = value

    return new
