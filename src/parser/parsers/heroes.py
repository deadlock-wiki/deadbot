import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.json_utils as json_utils
from .constants import OUTPUT_DIR


class HeroParser:
    def __init__(self, hero_data, abilities_data, parsed_abilities, localizations):
        self.hero_data = hero_data
        self.abilities_data = abilities_data
        self.parsed_abilities = parsed_abilities
        self.localizations = localizations

    def run(self):
        hero_keys = self.hero_data.keys()

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                hero_value = self.hero_data[hero_key]

                hero_stats = {
                    'Name': self.localizations.get(hero_key, None),
                    'BoundAbilities': self._parse_hero_abilities(hero_value),
                }

                hero_stats.update(
                    self._map_attr_names(hero_value['m_mapStartingStats'], maps.get_hero_attr)
                )

                hero_stats['SpiritScaling'] = self._parse_spirit_scaling(hero_value)
                weapon_stats = self._parse_hero_weapon(hero_value)
                hero_stats.update(weapon_stats)

                # Parse Level scaling
                if 'm_mapStandardLevelUpUpgrades' in hero_value:
                    level_scalings = hero_value['m_mapStandardLevelUpUpgrades']

                    hero_stats['LevelScaling'] = {}
                    for key in level_scalings:
                        hero_stats['LevelScaling'][maps.get_level_mod(key)] = level_scalings[key]

                all_hero_stats[hero_key] = json_utils.sort_dict(hero_stats)

                # Analysis - if more analyses of these similar nature are made, they can be moved to another file; for now it runs when parsed
                # Confirm the following stats are all 1
                # If any are not 1, the wiki should likely get this information added either to the hero infobox template or elsewhere, and the stat removed from the list below
                multipliers = ['TechRange', 'ReloadSpeed', 'TechDuration', 'ProcBuildUpRateScale']
                for mult_str in multipliers:
                    mult_value = hero_stats.get(mult_str, 1)
                    if mult_value != 1:
                        raise Exception(f'Hero {hero_key} has {mult_str} of {mult_value} instead of 1')

        json_utils.write(OUTPUT_DIR + 'json/hero-data.json', json_utils.sort_dict(all_hero_stats))

    def _parse_hero_abilities(self, hero_value):
        bound_abilities = hero_value['m_mapBoundAbilities']

        abilities = {}
        for ability_position, bound_ability_key in bound_abilities.items():
            # ignore any abilities without any parsed data
            if bound_ability_key not in self.parsed_abilities:
                continue
            abilities[ability_position] = self.parsed_abilities[bound_ability_key]

        mapped_abilities = self._map_attr_names(abilities, maps.get_bound_abilities)

        return mapped_abilities

    def _parse_hero_weapon(self, hero_value):
        weapon_stats = {}

        weapon_prim_id = hero_value['m_mapBoundAbilities']['ESlot_Weapon_Primary']
        weapon_prim = self.abilities_data[weapon_prim_id]['m_WeaponInfo']

        weapon_stats = {
            'BulletDamage': weapon_prim['m_flBulletDamage'],
            'RoundsPerSecond': 1 / weapon_prim['m_flCycleTime'],
            'ClipSize': weapon_prim['m_iClipSize'],
            'ReloadTime': weapon_prim['m_reloadDuration'],
        }

        weapon_stats['DPS'] = weapon_stats['BulletDamage'] * weapon_stats['RoundsPerSecond']
        return weapon_stats

    def _parse_spirit_scaling(self, hero_value):
        if 'm_mapScalingStats' not in hero_value:
            return None

        parsed_spirit_scaling = {}

        """ 
            Transform each value within m_mapScalingStats from
            
            "MaxMoveSpeed": {
                "eScalingStat": "ETechPower",
                "flScale": 0.04
            },
            
            to
            
            "MaxMoveSpeed": 0.04
        # `spirit_scalings` is a dictionary that contains scaling stats for a hero. Each key in
        # `spirit_scalings` corresponds to a specific attribute of the hero (e.g., "MaxMoveSpeed"),
        # and the value associated with each key is another dictionary that includes the scaling
        # information for that attribute.
        """
        spirit_scalings = hero_value['m_mapScalingStats']
        for hero_scaling_key, hero_scaling_value in spirit_scalings.items():
            parsed_spirit_scaling[maps.get_hero_attr(hero_scaling_key)] = hero_scaling_value[
                'flScale'
            ]

            # Ensure the only scalar in here is ETechPower
            if 'ETechPower' != hero_scaling_value['eScalingStat']:
                raise Exception(
                    f'Expected scaling key "ETechPower" but is: {hero_scaling_value["eScalingStat"]}'
                )

        return parsed_spirit_scaling

    # maps all keys in an object using the provided function
    def _map_attr_names(self, data, func):
        output_data = dict()
        for key in data:
            mapped_key = func(key)
            output_data[mapped_key] = data[key]

        return output_data
