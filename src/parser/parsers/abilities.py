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
                scale = self._get_scale(stat)
                if scale:
                    ability_data[key] = {'Value': value, 'Scale': scale}
                else:
                    ability_data[key] = value

            # Special handling for Patron's Damage Pulse, which stores stats in a unique location.
            if ability_key == 'citadel_ability_tier3boss_damage_pulse':
                modifiers_list = ability.get('m_AutoIntrinsicModifiers')
                if modifiers_list and isinstance(modifiers_list, list) and len(modifiers_list) > 0:
                    modifier = modifiers_list[0]
                    ability_data['PulseRadius'] = num_utils.assert_number(modifier.get('m_flRadius'))
                    ability_data['MaxTargets'] = num_utils.assert_number(modifier.get('m_iMaxTargets'))
                    ability_data['DamagePerPulse'] = num_utils.assert_number(modifier.get('m_flDamagePerPulse'))
                    ability_data['PulseInterval'] = num_utils.assert_number(modifier.get('m_flTickRate'))

            if 'm_vecAbilityUpgrades' in ability:
                ability_data['Upgrades'] = self._parse_upgrades(ability)
            else:
                ability_data['Upgrades'] = []

            formatted_ability_data = {}
            for attr_key, attr_value in ability_data.items():
                formatted_ability_data[attr_key] = num_utils.remove_uom(attr_value)

            all_abilities[ability_key] = json_utils.sort_dict(formatted_ability_data)

        return all_abilities

    def _parse_upgrades(self, ability):
        upgrade_sets = ability['m_vecAbilityUpgrades']
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

                # if stat has a base value, convert the upgrade value to the appropriate units
                stat = json_utils.deep_get(ability, 'm_mapAbilityProperties', prop)
                if stat:
                    value = self._convert_stat(stat, upgrade[key], value)

                if upgrade_type in ['EAddToBase', None]:
                    if parsed_upgrade_set.get(prop) is None:
                        parsed_upgrade_set[prop] = value
                    # if it is a dict (ie. for a scale value), assign the base value
                    elif isinstance(parsed_upgrade_set.get(prop), dict):
                        parsed_upgrade_set[prop]['Value'] = value

                elif upgrade_type in ['EAddToScale', 'EMultiplyScale']:
                    parsed_upgrade_set[prop] = {
                        'Value': parsed_upgrade_set.get(prop, 0),
                        'Scale': {
                            'Value': value,
                            'Type': maps.get_scale_type(scale_type),
                        },
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

        return self._convert_stat(stat, key, value)

    def _convert_stat(self, stat: dict, key: str, value: str | int | float):
        """Convert a value to the correct unit of measure and format based on the raw stat's information

        Args:
            stat (dict): Raw ability stat which includes information on its units and class
            key (str): Key of ability stat
            value (str | int | float): Value of ability stat

        Returns:
            int | float: Converted value
        """
        # if the value ends with "m", it is already converted to the correct units
        if isinstance(value, str) and value.endswith('m'):
            return num_utils.assert_number(value[:-1])

        # specific to ChannelMoveSpeed, a "-1" indicates stationary, so no need to convert units
        if key == 'ChannelMoveSpeed' and value == '-1':
            return -1

        units = stat.get('m_eDisplayUnits')
        strClass = stat.get('m_strCSSClass')

        # some ranges are written as "1500 2000" to denote a specific range
        if isinstance(value, str) and strClass == 'range':
            ranges = value.split(' ')
            if len(ranges) == 2:
                lower = num_utils.assert_number(ranges[0])
                upper = num_utils.assert_number(ranges[1])
                if units in ['EDisplayUnit_Meters', 'EDisplayUnit_MetersPerSecond']:
                    return f'{num_utils.convert_engine_units_to_meters(lower)} {num_utils.convert_engine_units_to_meters(upper)}'
                else:
                    return f'{lower} {upper}'

        value = num_utils.assert_number(value)

        if units in ['EDisplayUnit_Meters', 'EDisplayUnit_MetersPerSecond']:
            return num_utils.convert_engine_units_to_meters(value)

        return value

    def _get_scale(self, stat):
        """
        Get scale data for the ability attribute, which will refer to how the value of the attribute
        scales with another stat, usually Spirit
        """
        if 'm_subclassScaleFunction' in stat:
            scale = stat['m_subclassScaleFunction']
            # Only include scale with a value, as not sure what
            # any others mean so far.
            if 'm_flStatScale' in scale:
                return {
                    'Value': scale['m_flStatScale'],
                    'Type': maps.get_scale_type(scale.get('m_eSpecificStatScaleType', 'ETechPower')),
                }

        return None
