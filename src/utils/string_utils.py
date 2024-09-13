import re


def format_description(description, data):
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
        return str(data.get(key, ''))

    formatted_desc = re.sub(r'\{s:(.*?)\}', replace_match, desc)
    return formatted_desc


def string_to_number(string, decimal_places=None):
    """
    Convert string to a number, if possible.
    Otherwise return original string
    Args:
        string (str): string to be converted
        decimal_places (int): decimal places to be rounded to if string is a float
    """
    number = None
    try:
        number = int(string)
    except (TypeError, ValueError):
        try:
            number = float(string)
            if decimal_places is not None:
                number = round(number, decimal_places)
        except (TypeError, ValueError):
            number = string

    return number
