import parser.maps as maps
import utils.json_utils as json_utils
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
                #'Number': self._get_ability_num(ability_key),
            }

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
                    ability_data, ability['m_vecAbilityUpgrades']
                )

            formatted_ability_data = {}
            for attr_key, attr_value in ability_data.items():
                # strip attrs with value of 0, as that just means it is irrelevant
                if attr_value != '0':
                    formatted_ability_data[attr_key] = num_utils.remove_uom(attr_value)

            all_abilities[ability_key] = json_utils.sort_dict(formatted_ability_data)

        return all_abilities

    def _parse_upgrades(self, ability_data, upgrade_sets):
        parsed_upgrade_sets = []

        for index, upgrade_set in enumerate(upgrade_sets):
            parsed_upgrade_set = {}

            for upgrade in upgrade_set['m_vecPropertyUpgrades']:
                prop = None
                value = None
                upgrade_type = None
                scale_type = None

                for key in upgrade:
                    match key:
                        case 'm_strPropertyName':
                            prop = upgrade[key]

                        case 'm_strBonus':
                            value = num_utils.assert_number(upgrade[key])

                        case 'm_eUpgradeType':
                            upgrade_type = upgrade[key]

                        case 'm_eScaleStatFilter':
                            scale_type = upgrade[key]

                # TODO - handle different types of upgrades
                if upgrade_type in ['EAddToBase', None]:
                    parsed_upgrade_set[prop] = value
                elif upgrade_type == 'EAddToScale':
                    parsed_upgrade_set['Scale'] = {
                        'Prop': prop,
                        'Value': value,
                        'Type': maps.get_scale_type(scale_type),
                    }

            parsed_upgrade_sets.append(parsed_upgrade_set)

        return parsed_upgrade_sets
    
#     def _get_ability_num(self, ability_key):
#         for hero_key, hero_data in self.heroes_data.items():
#             print(hero_key, hero_data)
#             for ability_num, ability_data in hero_data["BoundAbilities"].items():
#                 if ability_data["Key"] == ability_key:
#                     return ability_num
#         raise ValueError(f"Ability {ability_key} not found in heroes data")

    
# def get_ability_num(ability_data):
#     a=1
    

