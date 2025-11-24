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
                rounded_value = num_utils.round_sig_figs(stripped_value, 3)

                if isinstance(rounded_value, float) and rounded_value.is_integer():
                    return str(int(rounded_value))

                return str(rounded_value)

            return value

        if key in IGNORE_KEYS:
            return f'IGNORED[{key}]'

        logger.warning(f'Could not find variable for key {key}')

        # return f'UNKNOWN[{key}]'
        raise Exception(f'Data not found for "{key}"')

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
