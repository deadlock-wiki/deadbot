import utils.json_utils as json_utils
import utils.string_utils as string_utils
import os
from loguru import logger


class GenericParser:
    """
    Lightly parse the generic data to have more readable keys.

    Validate structures used by the frontend to identify
    possible failure points in the case they are modified
    by Valve.
    """

    def __init__(self, output_dir, generic_data):
        self.STRUCTURE_KEYS_TO_VALIDATE = ['ObjectiveParams', 'RejuvParams', 'ItemPricePerTier']
        self.POSSIBLE_PREFIXES = ['m_str', 'm_map', 'm_n', 'm_fl', 'm_', 'fl', 'E', 'n']
        self.generic_data_dir = output_dir
        self.generic_data = generic_data

    def _read(self):
        if not os.path.exists(self.generic_data_dir):
            return None

        # Read existing generic data from file
        return json_utils.read(self.generic_data_dir)

    def run(self):
        # Parse generic data
        parsed_generics = self._remove_prefixes(self.generic_data, self.POSSIBLE_PREFIXES)

        # Read existing generic data
        existing_generics = self._read()

        # If there ie existing data, validate the structure
        if existing_generics is not None:
            invalid_keys = json_utils.validate_structures(
                existing_generics, parsed_generics, self.STRUCTURE_KEYS_TO_VALIDATE
            )

            if len(invalid_keys) > 0:
                logger.warning(
                    'A structure within Generic data has changed:'
                    + f' {invalid_keys}. Please verify the changes,'
                    + ' and update the frontend page [[Module:GenericData]] accordingly.'
                )

        return parsed_generics

    def _remove_prefixes(self, generic_data, possible_prefixes):
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
                value = self._remove_prefixes(value, possible_prefixes)
            elif isinstance(value, list):
                for i, elem in enumerate(value):
                    if isinstance(elem, dict):
                        value[i] = self._remove_prefixes(elem, possible_prefixes)

            new[new_key] = value

        return new
