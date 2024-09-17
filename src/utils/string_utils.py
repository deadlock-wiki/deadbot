import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import maps


def format_description(description, *data_sets):
    data = {}
    for data_set in data_sets:
        data.update(data_set)

    if isinstance(description, tuple):
        description = description[0]

    if description is None:
        return None

    # strip away all html tags for displaying as text
    description = re.sub(r'<span\b[^>]*>|<\/span>', '', description)
    return _replace_variables(description, data)


# format description with data. eg. "When you are above {s:LifeThreshold}% health"
# should become "When you are above 20% health"
def _replace_variables(desc, data):
    def replace_match(match):
        key = match.group(1)
        key = maps.override_localization(key)
        if key in data:
            value = str(data[key])
            # strip out "m" (metres), as it we just want the formatted
            # description should contain any units
            if value.endswith('m'):
                return value[:-1]

            return value
        return f'UNKNOWN[{key}]'

    formatted_desc = re.sub(r'\{s:(.*?)\}', replace_match, desc)
    return formatted_desc


def string_to_number(string):
    """
    Convert string to a number, if possible.
    Otherwise return original string
    """
    number = None
    try:
        number = int(string)
    except (TypeError, ValueError):
        try:
            number = float(string)
        except (TypeError, ValueError):
            number = string

    return number
