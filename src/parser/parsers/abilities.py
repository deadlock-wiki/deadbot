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
                'IsDisabled': ability.get('m_bDisabled', False),
            }

            stats = ability['m_mapAbilityProperties']
            for key in stats:
                stat = stats[key]
                value = self._get_stat_value(key, stat)
                ability_data[key] = value

            if 'm_vecAbilityUpgrades' not in ability:
                continue
            else:
                ability_data['Upgrades'] = self._parse_upgrades(ability_data, ability['m_vecAbilityUpgrades'])

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

            upgrades = upgrade_set.get('m_vecPropertyUpgrades')
            if upgrades is None:
                continue

            for upgrade in upgrades:
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
                elif upgrade_type in ['EAddToScale', 'EMultiplyScale']:
                    parsed_upgrade_set['Scale'] = {
                        'Prop': prop,
                        'Value': value,
                        'Type': maps.get_scale_type(scale_type),
                    }

            parsed_upgrade_sets.append(parsed_upgrade_set)

        return parsed_upgrade_sets

    def _get_stat_value(self, key, stat):
        value = None

        if 'm_strValue' in stat:
            value = stat['m_strValue']
        elif 'm_strVAlue' in stat:
            value = stat['m_strVAlue']
        else:
            return None

        # if the value ends with "m", it is already converted to the correct units
        if isinstance(value, str) and value.endswith('m'):
            return num_utils.assert_number(value[:-1])

        # specific to ChannelMoveSpeed, a "-1" indicates stationary, so no need to convert units
        if key == 'ChannelMoveSpeed' and value == '-1':
            return -1

        units = stat.get('m_eDisplayUnits')
        strClass = stat.get('m_strCSSClass')

        # some ranges are written as "1500 2000" to denote a specific range
        if strClass == 'range':
            ranges = value.split(' ')
            if len(ranges) == 2:
                lower = num_utils.assert_number(ranges[0])
                upper = num_utils.assert_number(ranges[1])
                if units in ['EDisplayUnit_Meters', 'EDisplayUnit_MetersPerSecond']:
                    return f'{lower/4} {upper/4}'
                else:
                    return f'{lower} {upper}'

        value = num_utils.assert_number(value)

        if units in ['EDisplayUnit_Meters', 'EDisplayUnit_MetersPerSecond']:
            return num_utils.assert_number(value / 4)

        return value
