import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils import json
import maps as maps


class HeroParser:
    def __init__(self, hero_data, abilities_data, localizations):
        self.hero_data = hero_data
        self.abilities_data = abilities_data
        self.localizations = localizations

    def run(self):
        hero_keys = self.hero_data.keys()

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                hero_value = self.hero_data[hero_key]

                hero_stats = {
                    'Name': self.localizations['names'].get(hero_key, None),
                }

                hero_stats.update(
                    self._map_attr_names(hero_value['m_mapStartingStats'], maps.get_hero_attr)
                )

                # Parse Tech scaling
                if 'm_mapScalingStats' in hero_value:
                    # Move scaling data under TechScaling key
                    hero_stats['SpiritScaling'] = {}

                    # Transform each value within m_mapScalingStats from

                    # "MaxMoveSpeed": {
                    #     "eScalingStat": "ETechPower",
                    #     "flScale": 0.04
                    # },

                    # to

                    # "MaxMoveSpeed": 0.04
                    spirit_scalings = hero_value['m_mapScalingStats']
                    for hero_scaling_key, hero_scaling_value in spirit_scalings.items():
                        hero_stats['TechScaling'][maps.get_hero_attr(hero_scaling_key)] = (
                            hero_scaling_value['flScale']
                        )

                        # Ensure the only scalar in here is ETechPower
                        if 'ETechPower' != hero_scaling_value['eScalingStat']:
                            raise Exception(
                                f"Expected scaling key 'ETechPower' but is: {hero_scaling_value["eScalingStat"]}"
                            )

                weapon_stats = self._parse_hero_weapon(hero_value)
                hero_stats.update(weapon_stats)

                # Parse Level scaling
                if 'm_mapStandardLevelUpUpgrades' in hero_value:
                    level_scalings = hero_value['m_mapStandardLevelUpUpgrades']

                    hero_stats['LevelScaling'] = {}
                    for key in level_scalings:
                        hero_stats['LevelScaling'][maps.get_level_mod(key)] = level_scalings[key]

                all_hero_stats[hero_key] = sort_dict(hero_stats)

        json.write(self.OUTPUT_DIR + 'json/hero-data.json', sort_dict(all_hero_stats))

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

        weapon_stats['Dps'] = weapon_stats['BulletDamage'] * weapon_stats['BulletsPerSec']
        return weapon_stats

    # maps all keys in an object using the provided function
    def _map_attr_names(self, data, func):
        output_data = dict()
        for key in data:
            mapped_key = func(key)
            output_data[mapped_key] = data[key]

        return output_data
