from utils import num_utils
from utils.json_utils import deep_get


def parse_item_upgrades(item_value):
    property_upgrades = {}
    vec_ability_upgrades = item_value.get('m_vecAbilityUpgrades', [])
    for ability_upgrade in vec_ability_upgrades:
        vec_property_upgrades = ability_upgrade.get('m_vecPropertyUpgrades', [])
        parsed_upgrade_props = _parse_upgrade_props(vec_property_upgrades)
        property_upgrades.update(parsed_upgrade_props)

    return property_upgrades


def parse_corrupted_upgrades(item_value):
    upgrades = deep_get(item_value, 'm_CorruptedItemInfo', 'm_Upgrade', 'm_vecPropertyUpgrades')
    if not upgrades:
        return None
    return _parse_upgrade_props(upgrades)


def _parse_upgrade_props(props):
    parsed_props = {}
    for upgrade_prop in props:
        prop_name = upgrade_prop.get('m_strPropertyName')
        bonus_str = upgrade_prop.get('m_strBonus')

        if not prop_name or bonus_str is None:
            continue

        bonus_value = num_utils.assert_number(bonus_str)
        parsed_props[prop_name] = bonus_value

    return parsed_props
