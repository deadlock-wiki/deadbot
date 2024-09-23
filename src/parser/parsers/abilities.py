import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from .constants import OUTPUT_DIR
import maps as maps
import utils.json_utils as json_utils
import utils.string_utils as string_utils
import utils.num_utils as num_utils


class AbilityParser:
    def __init__(self, abilities_data, heroes_data, localizations):
        self.abilities_data = abilities_data
        self.heroes_data = heroes_data
        self.localizations = localizations

    def run(self):
        all_abilities = {}

        for ability_key in self.abilities_data:
            ability = self.abilities_data[ability_key]
            if type(ability) is not dict:
                continue

            if 'm_eAbilityType' not in ability:
                continue

            if ability['m_eAbilityType'] not in ['EAbilityType_Signature', 'EAbilityType_Ultimate']:
                continue

            ability_data = {
                'Key': ability_key,
                'Name': self.localizations.get(ability_key, None),
            }

            # hero name that uses this ability, relevant for formatting descriptions
            hero_name = self._find_hero_name(ability_key)

            stats = ability['m_mapAbilityProperties']
            for key in stats:
                stat = stats[key]

                value = None

                if 'm_strValue' in stat:
                    value = stat['m_strValue']

                elif 'm_strVAlue' in stat:
                    value = stat['m_strVAlue']

                ability_data[key] = value

            if 'm_vecAbilityUpgrades' not in ability:
                # print(ability.get('Name'), 'missing upgrades')
                continue
            else:
                ability_data['Upgrades'] = self._parse_upgrades(
                    ability_data, ability['m_vecAbilityUpgrades'], hero_name
                )

            description = (self.localizations.get(ability_key + '_desc'),)

            # required variables to insert into the description
            format_vars = (ability_data, maps.KEYBIND_MAP, {'hero_name': hero_name})

            ability_data['Description'] = string_utils.format_description(description, *format_vars)

            formatted_ability_data = {}
            for attr_key, attr_value in ability_data.items():
                # strip attrs with value of 0, as that just means it is irrelevant
                if attr_value != '0':
                    formatted_ability_data[attr_key] = num_utils.remove_uom(attr_value)

            all_abilities[ability_key] = json_utils.sort_dict(formatted_ability_data)
        json_utils.write(OUTPUT_DIR+'/json/ability-data.json', 
            json_utils.sort_dict(all_abilities)
        )

        return all_abilities

    def _parse_upgrades(self, ability_data, upgrade_sets, hero_name):
        parsed_upgrade_sets = []

        for index, upgrade_set in enumerate(upgrade_sets):
            parsed_upgrade_set = {}

            for upgrade in upgrade_set['m_vecPropertyUpgrades']:
                prop = None
                value = None
                upgrade_type = None

                for key in upgrade:
                    match key:
                        case 'm_strPropertyName':
                            prop = upgrade[key]

                        case 'm_strBonus':
                            value = num_utils.assert_number(upgrade[key])

                        case 'm_eUpgradeType':
                            upgrade_type = upgrade[key]

                # TODO - handle different types of upgrades
                if upgrade_type is None:
                    parsed_upgrade_set[prop] = value

            # add and format the description of the ability upgrade
            # descriptions include t1, t2, and t3 denoting the tier
            desc_key = f'{ability_data["Key"]}_t{index+1}_desc'
            if desc_key in self.localizations:
                desc = self.localizations[desc_key]

                # required variables to insert into the description
                format_vars = (
                    parsed_upgrade_set,
                    maps.KEYBIND_MAP,
                    {'ability_key': index},
                    {'hero_name': hero_name},
                )

                formatted_desc = string_utils.format_description(desc, *format_vars)
                parsed_upgrade_set['Description'] = formatted_desc

            # create our own description if none exists
            else:
                desc = ''
                for attr, value in parsed_upgrade_set.items():
                    str_value = str(value)

                    uom = self._get_uom(attr, str_value)

                    # update data value to have no unit of measurement
                    num_value = num_utils.remove_uom(str_value)
                    parsed_upgrade_set[prop] = num_value

                    prefix = ''
                    # attach "+" if the value is positive
                    if isinstance(value, str) or not value < 0:
                        prefix = '+'

                    desc += f'{prefix}{num_value}{uom} {self._get_ability_display_name(attr)} and '

                # strip off extra "and" from description
                desc = desc[: -len(' and ')]
                parsed_upgrade_set['Description'] = desc

            parsed_upgrade_sets.append(parsed_upgrade_set)

        return parsed_upgrade_sets

    def _find_hero_name(self, ability_key, return_key_or_localized='localized'):
        for hero_key, hero in self.heroes_data.items():
            # ignore non-dicts that live in the hero data
            if not isinstance(hero, dict):
                continue

            abilities = hero['m_mapBoundAbilities']
            for i in range(1, 5):
                key = f'ESlot_Signature_{str(i)}'
                if key in abilities and abilities[key] == ability_key:
                    if return_key_or_localized == 'key':
                        return hero_key
                    elif return_key_or_localized == 'localized':
                        return self.localizations[hero_key]
                    else:
                        raise Exception(f'Unknown key_or_localized value {return_key_or_localized}')

        return None

    def _get_ability_display_name(self, attr):
        OVERRIDES = {
            'BonusHealthRegen': 'HealthRegen_label',
            'BarbedWireRadius': 'Radius_label',
            'BarbedWireDamagePerMeter': 'DamagePerMeter_label',
            # capital "L" for some reason...
            'TechArmorDamageReduction': 'TechArmorDamageReduction_Label',
            'DamageAbsorb': 'DamageAbsorb_Label',
            'InvisRegen': 'InvisRegen_Label',
            'EvasionChance': 'EvasionChance_Label',
            'DelayBetweenShots': 'DelayBetweenShots_Label',
        }

        if attr in OVERRIDES:
            return self.localizations[OVERRIDES[attr]]

        localized_key = f'{attr}_label'
        if localized_key not in self.localizations:
            print(f'Missing label for key {localized_key}')
            return
        return self.localizations[localized_key]

    def _get_uom(self, attr, value):
        localized_key = f'{attr}_postfix'

        if localized_key in self.localizations:
            return self.localizations[localized_key]

        # Sometimes the uom is attached to the end of the value
        unit = ''
        if value.endswith('m'):
            unit = 'm'

        if value.endswith('s'):
            unit = 's'

        return unit
