import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.json_utils as json_utils
from .constants import OUTPUT_DIR, ENGINE_UNITS_PER_METER


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

                # Change formatting on some numbers to match whats shown in game
                hero_stats['StaminaCooldown'] = 1 / hero_stats['StaminaRegenPerSecond']
                hero_stats['CritDamageReceivedScale'] = hero_stats['CritDamageReceivedScale'] - 1
                hero_stats['TechRange'] = hero_stats['TechRange'] - 1
                hero_stats['TechDuration'] = hero_stats['TechDuration'] - 1
                hero_stats['ReloadSpeed'] = hero_stats['ReloadSpeed'] - 1

                hero_stats['SpiritScaling'] = self._parse_spirit_scaling(hero_value)
                weapon_stats = self._parse_hero_weapon(hero_value)
                hero_stats.update(weapon_stats)

                # Determine hero's ratio of heavy to light melee damage
                heavy_light_ratio = hero_stats['HeavyMeleeDamage'] / hero_stats['LightMeleeDamage']

                # Parse Level scaling
                if 'm_mapStandardLevelUpUpgrades' in hero_value:
                    level_scalings = hero_value['m_mapStandardLevelUpUpgrades']

                    hero_stats['LevelScaling'] = {}
                    for key in level_scalings:
                        hero_stats['LevelScaling'][maps.get_level_mod(key)] = level_scalings[key]

                    # Spread the MeleeDamage level scaling into Light and Heavy, using H/L ratio
                    if 'MeleeDamage' in hero_stats['LevelScaling']:
                        hero_stats['LevelScaling']['LightMeleeDamage'] = hero_stats['LevelScaling']['MeleeDamage']
                        hero_stats['LevelScaling']['HeavyMeleeDamage'] = hero_stats['LevelScaling']['MeleeDamage'] * heavy_light_ratio
                        del hero_stats['LevelScaling']['MeleeDamage']

                    # Remove scalings if they are 0.0
                    hero_stats['LevelScaling'] = {k: v for k, v in hero_stats['LevelScaling'].items() if v != 0.0}
                    

                all_hero_stats[hero_key] = json_utils.sort_dict(hero_stats)

        json_utils.write(OUTPUT_DIR + 'json/hero-data.json', json_utils.sort_dict(all_hero_stats))
        return all_hero_stats

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
            'ReloadMovespeed': int(weapon_prim['m_flReloadMoveSpeed']) / 10000,
            'ReloadDelay': weapon_prim.get('m_flReloadSingleBulletsInitialDelay', 0),
            'ReloadSingle': weapon_prim.get('m_bReloadSingleBullets', False),
            'BulletSpeed': self._calc_bullet_velocity(weapon_prim['m_BulletSpeedCurve']['m_spline']),
            'FalloffStartRange': weapon_prim['m_flDamageFalloffStartRange'] / ENGINE_UNITS_PER_METER,
            'FalloffEndRange': weapon_prim['m_flDamageFalloffEndRange'] / ENGINE_UNITS_PER_METER,
            'FalloffStartScale': weapon_prim['m_flDamageFalloffStartScale'],
            'FalloffEndScale': weapon_prim['m_flDamageFalloffEndScale'],
            'FalloffBias': weapon_prim['m_flDamageFalloffBias'],
            'BulletGravityScale': weapon_prim['m_flBulletGravityScale'],
            #'BulletRadius': weapon_prim['m_flBulletRadius'] / ENGINE_UNITS_PER_METER,
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

    def _calc_bullet_velocity(self, spline):
        """Calculates bullet velocity of a spline, ensuring its linear"""
        """
        Transforms
        [
            {
                "x": 0.0,
                "y": 23999.998047,
                "m_flSlopeIncoming": 0.0,
                "m_flSlopeOutgoing": 0.0
            },
            {
                "x": 100.0,
                "y": 23999.998047,
                "m_flSlopeIncoming": 0.0,
                "m_flSlopeOutgoing": 0.0
            }
        ]

        to

        23999.998047
        """

        # Confirm its linear
        for point in spline:
            if point['m_flSlopeIncoming'] != 0 or point['m_flSlopeOutgoing'] != 0:
                raise Exception('Bullet speed curve is not linear')

        # Confirm its constant
        last_y = spline[0]['y']
        for point in spline:
            if point['y'] != last_y:
                raise Exception('Bullet speed curve is not constant')

        # If constant, return the y
        return int(round(last_y / ENGINE_UNITS_PER_METER, 0))
