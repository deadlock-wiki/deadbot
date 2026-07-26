import parser.maps as maps
from . import utils
import utils.json_utils as json_utils
import utils.num_utils as num_utils
from .upgrades import parse_upgrades
from .modifiers import parse_modifiers
from loguru import logger

# Scale applied to a stat when the game files do not specify one
DEFAULT_STAT_SCALE = 1


class AbilityParser:
    def __init__(self, abilities_data, heroes_data, localizations):
        self.abilities_data = abilities_data
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
            'BehaviourBits': maps.get_behaviour_bits(ability.get('m_AbilityBehaviorsBits')),
        }

        stats = ability.get('m_mapAbilityProperties', {})
        for key in stats:
            stat = stats[key]
            value = self._get_stat_value(key, stat)
            scale = self._get_scale(stat, value)
            if scale:
                ability_data[key] = {'Value': value, 'Scale': scale}
            else:
                ability_data[key] = value

        ability_data.update(parse_upgrades(ability))
        ability_data.update(parse_modifiers(ability))

        formatted_ability_data = {}
        for attr_key, attr_value in ability_data.items():
            formatted_ability_data[attr_key] = num_utils.remove_uom(attr_value)

        return json_utils.sort_dict(formatted_ability_data)

    def _get_stat_value(self, key, stat):
        if 'm_strValue' not in stat:
            return
        value = stat['m_strValue']

        return utils.convert_stat(stat, key, value)

    def _get_scale(self, stat, value):
        """
        Get scale data for the ability attribute, which will refer to how the value of the attribute
        scales with another stat, such as Spirit, Ability Duration, Range or Cooldown

        Returns a single scale, or a list of them when the attribute scales with several stats
        """
        scale_func = stat.get('m_subclassScaleFunction')
        if not isinstance(scale_func, dict):
            return

        # Valve disables a scale function in place rather than removing it
        if scale_func.get('m_bFunctionDisabled'):
            return

        # an attribute of zero stays zero no matter how the hero's duration, range or cooldown
        # scale it, so leave it as a plain zero for the output to strip
        if num_utils.is_zero(value) and 'm_flStatScale' not in scale_func:
            return

        scales = [{'Value': scale_value, 'Type': maps.get_scale_type(scale_type)} for scale_type, scale_value in self._get_scale_stats(scale_func)]

        if len(scales) == 1:
            return scales[0]

        return scales

    def _get_scale_stats(self, scale_func):
        """
        Work out which of the hero's stats an ability attribute grows with, and at what rate each
        of them applies

        One attribute can grow with several hero stats at once, which the game files describe
        across three fields:
          - `m_eSpecificStatScaleType` names a single hero stat, eg. ETechPower for Spirit Power
          - `m_flStatScale` is the rate the attribute grows at per point of that named stat, and
            of no other. It is left out when the rate is 1, ie. the hero's stat applies in full
          - `m_vecScalingStats` lists every hero stat involved, the named one included. All the
            others apply in full

        Lash's Death Slam uses all three. Its throw distance names ETechPower at a rate of 0.14
        and lists [ETechPower, ETechRange], meaning the distance grows by 0.14 for every point of
        Spirit Power, and on top of that grows in full with the hero's Ability Range. So it
        returns [(ETechPower, 0.14), (ETechRange, 1)].

        The named stat is returned first, being the one whose rate the game bothered to spell
        out, and so the one a description is most likely to quote.
        """
        named_stat = scale_func.get('m_eSpecificStatScaleType') or maps.class_to_scale_enum(scale_func.get('_class', ''))
        listed_stats = [scale_type for scale_type in scale_func.get('m_vecScalingStats') or [] if scale_type]

        if not named_stat:
            # with no stat named, the rate belongs to the first stat listed, falling back to
            # spirit as it is by far the most common stat for an attribute to grow with
            named_stat = listed_stats[0] if listed_stats else 'ETechPower'

        named_rate = num_utils.assert_number(scale_func.get('m_flStatScale', DEFAULT_STAT_SCALE))

        stats = [(named_stat, named_rate)]
        stats += [(scale_type, DEFAULT_STAT_SCALE) for scale_type in listed_stats if scale_type != named_stat]

        return stats
