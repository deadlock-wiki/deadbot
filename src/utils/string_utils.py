import re


def format_description(description, data):
    print('--', description)

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
        return data.get(key, '')

    formatted_desc = re.sub(r'\{s:(.*?)\}', replace_match, desc)
    return formatted_desc
