import parser.maps as maps
from . import utils
import utils.json_utils as json_utils
import utils.num_utils as num_utils
from .upgrades import parse_upgrades
from loguru import logger


class AbilityParser:
    def __init__(self, abilities_data, heroes_data, localizations):
        # Wrap with a case-insensitive dict so inconsistent capitalization in
        # Valve's source data (e.g. AbilitYCharges, m_strVAlue) doesn't make
        # lookups silently miss. Original key casing is preserved for output.
        self.abilities_data = json_utils.wrap_case_insensitive(abilities_data)
        self.heroes_data = heroes_data
        self.localizations = localizations

    def run(self):
        all_abilities = {}
        ability_key = ''
        try:
            for ability_key in self.abilities_data:
                ability = self._parse_ability(ability_key)
                if ability:
                    all_abilities[ability_key] = ability

            return all_abilities
        except Exception as e:
            logger.error(f'Failed to parse ability {ability_key} - {e}')
            raise e

    def _parse_ability(self, ability_key):
        ability = self.abilities_data[ability_key]

        if not isinstance(ability, dict):
            return

        if 'm_eAbilityType' not in ability:
            return

        if ability['m_eAbilityType'] not in ['EAbilityType_Innate', 'EAbilityType_Signature', 'EAbilityType_Ultimate']:
            return

        ability_data = {
            'Key': ability_key,
            'Name': self.localizations.get(ability_key, None),
            'IsDisabled': ability.get('m_bDisabled', False),
        }

        stats = ability.get('m_mapAbilityProperties', {})
        for key in stats:
            stat = stats[key]
            value = self._get_stat_value(key, stat)
            scale = self._get_scale(stat)
            if scale:
                ability_data[key] = {'Value': value, 'Scale': scale}
            else:
                ability_data[key] = value

        if 'm_vecAbilityUpgrades' in ability:
            ability_data['Upgrades'] = parse_upgrades(ability)
        else:
            ability_data['Upgrades'] = []

        formatted_ability_data = {}
        for attr_key, attr_value in ability_data.items():
            formatted_ability_data[attr_key] = num_utils.remove_uom(attr_value)

        return json_utils.sort_dict(formatted_ability_data)

    def _get_stat_value(self, key, stat):
        # Case-insensitive lookup handles the 'm_strVAlue' typo variant.
        if 'm_strValue' not in stat:
            return
        value = stat['m_strValue']

        return utils.convert_stat(stat, key, value)

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

        return
