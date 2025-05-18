import sys
import os
import re

from loguru import logger

from utils import num_utils

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import parser.maps as maps


def format_description(description, *data_sets):
    """
        Find and replace any variables inside of the game's description, in addition
        to removing html tags.
        Variables come in the form of "{s:<var_name>}"

    Args:
        description (str): the localized string containing variables
        *data_sets: any number of objects to provide a source to replace the variables

    Example:
        "<span class=\"highlight\">+{s:AbilityCastRange}m</span> Cast Range and gain <span class=\"highlight\">+{s:WeaponDamageBonus}</span> Weapon Damage for {s:WeaponDamageBonusDuration}s"
    ->  "+7 Weapon Damage for 10s after teleporting with Flying Cloak"
    """  # noqa: E501
    data = {}
    for data_set in data_sets:
        data.update(data_set)

    if isinstance(description, tuple):
        description = description[0]

    if description is None:
        return None

    # remove <Panel ...></Panel> tags until we properly support them
    description = re.sub(r'<Panel\b[^>]*>', '', description)
    description = description.replace('</Panel>', '')

    # keybind icons are formatted as {g:citadel_keybind:<key_name>}
    description = re.sub(r"\{g:citadel_keybind:'([^']+)'\}", _replace_keybind, description)

    return _replace_variables(description, data)


# Keys to ignore errors, as they are manually verified as having no valid override
IGNORE_KEYS = [
    'BonusMaxStacks',
    'SlideEvasionChance',
    'BonusLossPerDeath',
    'SalvageBonus_Health',
    'ProjectileRedirectCount',
    'TurretHealthScaling',
    'DisarmDuration',
    '​ไซเลนเซอร์​adius',
]

KEYBIND_MAP = {
    'Attack': '{{Mouse|1}}',
    'ADS': '{{Mouse|2}}',
    'AltCast': '{{Mouse|3}}',
    'Reload': 'R',
    'Roll': 'Shift',
    'Mantle': 'Space',
    'Crouch': 'Ctrl',
    'Ability1': '1',
    'Ability2': '2',
    'Ability3': '3',
    'Ability4': '4',
    'MoveDown': 'Down',
    'MoveForward': 'Forward',
}


def _replace_keybind(match):
    key = match.group(1)
    replace_string = KEYBIND_MAP.get(key)

    if replace_string is None:
        raise Exception(f'Missing keybind map for {key}')

    start, end = match.span()

    before = match.string[start - 1] if start > 0 else ''
    after = match.string[end] if end < len(match.string) else ''

    # if not surrounded by html tags or spaces, add spaces
    prefix = '' if before in ['>', ' '] else ' '
    suffix = '' if after in ['<', ' '] else ' '

    return f'{prefix}{replace_string}{suffix}'


# format description with data. eg. "When you are above {s:LifeThreshold}% health"
# should become "When you are above 20% health"
def _replace_variables(desc, data):
    def replace_match(match):
        key = match.group(1)
        key = maps.override_localization(key)
        if key in data:
            value = str(data[key])

            # strip out units of measure to prevent duplicates eg. "Cooldown reduced by 5ss"
            stripped_value = num_utils.remove_uom(value)
            if type(stripped_value) in [float, int]:
                return str(stripped_value)

            return value

        if key in IGNORE_KEYS:
            return f'IGNORED[{key}]'

        logger.warning(f'Could not find variable for key {key}')
        return f'UNKNOWN[{key}]'
        # raise Exception(f'Data not found for "{key}"')

    formatted_desc = re.sub(r'\[?\{s:(.*?)\}\]?', replace_match, desc)
    return formatted_desc


def remove_letters(input_string):
    """Remove letters from a string. Eg. -4.5m -> -4.5"""
    return re.sub(r'[^0-9.\-]', '', input_string)


def is_truthy(string):
    TRUE_THO = [
        True,
        'true',
        'True',
        'TRUE',
        't',
        'T',
        1,
    ]
    return string in TRUE_THO


def remove_prefix(str, prefix):
    """
    Attempt to remove a given prefix from a str
    remove_prefix('m_nAbilityCastRange', 'm_n') -> 'AbilityCastRange'
    """
    if (
        len(str) > len(prefix)  # Key should be able to fit the prefix
        and str.startswith(prefix)  # Key starts with prefix
        and str[len(prefix)].isupper()  # Character after prefix is uppercase
    ):
        str = str.split(prefix)[1]

    return str
