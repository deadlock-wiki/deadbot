from utils import num_utils


def parse_property_upgrades(item_value):
    property_upgrades = {}
    vec_ability_upgrades = item_value.get('m_vecAbilityUpgrades', [])
    for ability_upgrade in vec_ability_upgrades:
        vec_property_upgrades = ability_upgrade.get('m_vecPropertyUpgrades', [])
        for prop_upgrade in vec_property_upgrades:
            prop_name = prop_upgrade.get('m_strPropertyName')
            bonus_str = prop_upgrade.get('m_strBonus')

            if not prop_name or bonus_str is None:
                continue

            bonus_value = num_utils.assert_number(bonus_str)
            property_upgrades[prop_name] = bonus_value

    return property_upgrades
