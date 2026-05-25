import utils.string_utils as string_utils


class MiscParser:
    """
    Parses misc.vdata by stripping prefixes and filtering out internal data,
    then uploads the whole thing.
    Same approach as GenericParser.
    """

    # Prefixes to strip from keys, sorted longest-first to prevent
    # partial matches (e.g. "m_nav" before "m_n")
    PREFIXES = sorted(
        [
            'm_fl',
            'm_b',
            'm_n',
            'm_i',
            'm_str',
            'm_vec',
            'm_map',
            'm_e',
            'm_subclass',
            'm_s',
            'm_',
        ],
        key=len,
        reverse=True,
    )

    # Internal metadata keys to remove
    METADATA_KEYS = {
        '_class',
        '_my_subclass_name',
        '_base',
        '_not_pickable',
        'generic_data_type',
    }

    def __init__(self, misc_data):
        self.misc_data = misc_data

    def run(self):
        parsed = self._remove_prefixes(self.misc_data, self.PREFIXES)
        return parsed

    def _remove_prefixes(self, data, prefixes):
        """Recursively strip prefixes from keys and filter out internal data."""
        if isinstance(data, dict):
            result = {}

            for key, value in data.items():
                # Skip internal metadata keys
                if key in self.METADATA_KEYS:
                    continue

                # Skip base class definitions
                if key.endswith('_base'):
                    continue

                # Strip prefix from key
                clean_key = key
                for prefix in prefixes:
                    clean_key = string_utils.remove_prefix(key, prefix)
                    if clean_key != key:
                        break

                # Force-strip m_ prefix when followed by lowercase
                # e.g. m_modifierProvidedByAura -> modifierProvidedByAura
                if clean_key.startswith('m_') and len(clean_key) > 2:
                    clean_key = clean_key[2:]

                # Recurse into nested structures
                if isinstance(value, dict):
                    value = self._remove_prefixes(value, prefixes)
                elif isinstance(value, list):
                    value = self._remove_prefixes_from_list(value, prefixes)

                # Skip empty containers after filtering
                if isinstance(value, (dict, list)) and len(value) == 0:
                    continue

                result[clean_key] = value

            return result if result else {}

        elif isinstance(data, list):
            return self._remove_prefixes_from_list(data, prefixes)

        return data

    def _remove_prefixes_from_list(self, data, prefixes):
        result = []
        for item in data:
            if isinstance(item, dict):
                parsed = self._remove_prefixes(item, prefixes)
                if parsed:
                    result.append(parsed)
            else:
                result.append(item)
        return result if result else []
