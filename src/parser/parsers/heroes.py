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

                # Lore, Playstyle, and Role keys from localization
                for key in ['Lore', 'Playstyle', 'Role']:
                    # i.e. hero_kelvin_lore which is a key in localization
                    hero_stats[key] = hero_key + '_' + key.lower() 

                # Determine hero's ratio of heavy to light melee damage
                hl_ratio = hero_stats['HeavyMeleeDamage'] / hero_stats['LightMeleeDamage']

                # Parse Level scaling
                if 'm_mapStandardLevelUpUpgrades' in hero_value:
                    level_scalings = hero_value['m_mapStandardLevelUpUpgrades']

                    hero_stats['LevelScaling'] = {}
                    for key in level_scalings:
                        hero_stats['LevelScaling'][maps.get_level_mod(key)] = level_scalings[key]

                    # Spread the MeleeDamage level scaling into Light and Heavy, using H/L ratio
                    if 'MeleeDamage' in hero_stats['LevelScaling']:
                        md_scalar = hero_stats['LevelScaling']['MeleeDamage']
                        hero_stats['LevelScaling']['LightMeleeDamage'] = md_scalar

                        hero_stats['LevelScaling']['HeavyMeleeDamage'] = md_scalar * hl_ratio
                        del hero_stats['LevelScaling']['MeleeDamage']

                    # Remove scalings if they are 0.0
                    hero_stats['LevelScaling'] = {
                        k: v for k, v in hero_stats['LevelScaling'].items() if v != 0.0
                    }

                all_hero_stats[hero_key] = json_utils.sort_dict(hero_stats)

        json_utils.write(OUTPUT_DIR + 'json/hero-data.json', json_utils.sort_dict(all_hero_stats))

        # Write non-constant stats to json file
        self._write_non_constants_stats(all_hero_stats)

        return all_hero_stats
    
    def _write_non_constants_stats(self, all_hero_stats):
        """
        Writes list of non-constant stats to json file.

        Returns non_constants_stats dict, where elements are true if they are non-constant.

        Non-constant stats are ones that will be displayed 
        on the deadlocked.wiki/Hero_Comparison page, among others in the future.
        """
        # Using 'non_constant' instead of 'variable' as 'variable' may indicate something else
        # Storing in dict with bool entry instead of list so its hashable on the frontend

        heroes_data = all_hero_stats.copy()
        stats_previous_value = {}
        non_constant_stats = {}

        # Iterate heroes
        for hero_key, hero_data in heroes_data.items():
            # Iterate hero stats
            for stat_key, stat_value in hero_data.items():
                # Must not be a container type, nor a bool
                stat_value_type = type(stat_value)
                if stat_value_type not in [int, float, str, bool]:
                    continue

                # Ensure the data isn't a localization key
                if stat_value_type == str and (any(str_to_match in stat_value for str_to_match in ['hero_', 'weapon_']) or stat_key == 'Name'):
                    continue

                # Add the stat's value to the dict
                if stat_key not in stats_previous_value:
                    stats_previous_value[stat_key] = stat_value

                # If its already tracked, and is different to current value, mark as non-constant
                else:
                    if stats_previous_value[stat_key] != stat_value:
                        non_constant_stats[stat_key] = True

        json_utils.write(OUTPUT_DIR + 'json/hero-non-constants.json', json_utils.sort_dict(non_constant_stats))
        

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

        # Parse weapon stats
        weapon_prim = self.abilities_data[weapon_prim_id]['m_WeaponInfo']
        w = weapon_prim

        weapon_stats = {
            'BulletDamage': w['m_flBulletDamage'],
            'RoundsPerSecond': 1 / w['m_flCycleTime'],
            'ClipSize': w['m_iClipSize'],
            'ReloadTime': w['m_reloadDuration'],
            'ReloadMovespeed': float(w['m_flReloadMoveSpeed']) / 10000,
            'ReloadDelay': w.get('m_flReloadSingleBulletsInitialDelay', 0),
            'ReloadSingle': w.get('m_bReloadSingleBullets', False),
            'BulletSpeed': self._calc_bullet_velocity(w['m_BulletSpeedCurve']['m_spline']),
            'FalloffStartRange': w['m_flDamageFalloffStartRange'] / ENGINE_UNITS_PER_METER,
            'FalloffEndRange': w['m_flDamageFalloffEndRange'] / ENGINE_UNITS_PER_METER,
            'FalloffStartScale': w['m_flDamageFalloffStartScale'],
            'FalloffEndScale': w['m_flDamageFalloffEndScale'],
            'FalloffBias': w['m_flDamageFalloffBias'],
            'BulletGravityScale': w['m_flBulletGravityScale'],
            #'BulletRadius': w['m_flBulletRadius'] / ENGINE_UNITS_PER_METER,
            'BulletsPerShot': w['m_iBullets'],
        }

        weapon_stats['DPS'] = weapon_stats['BulletDamage'] * weapon_stats['RoundsPerSecond'] * weapon_stats['BulletsPerShot']

        # Calc sustained DPS
        if weapon_stats['ReloadSingle']:
            time_to_reload = weapon_stats['ReloadTime'] * weapon_stats['ClipSize']
        else:
            time_to_reload = weapon_stats['ReloadTime']
        time_to_reload += weapon_stats['ReloadDelay']
        time_to_empty_clip = weapon_stats['ClipSize'] / weapon_stats['RoundsPerSecond']
        weapon_stats['SustainedDPS'] = weapon_stats['DPS'] * (time_to_empty_clip / (time_to_empty_clip + time_to_reload))

        weapon_stats['WeaponName'] = weapon_prim_id
        # i.e. citadel_weapon_kelvin_set to citadel_weapon_hero_kelvin_set
        weapon_stats['WeaponDescription'] = weapon_prim_id.replace(
            'citadel_weapon_', 'citadel_weapon_hero_'
        )

        # Parse weapon types
        shop_ui_weapon_stats = hero_value['m_ShopStatDisplay']['m_eWeaponStatsDisplay']
        if 'm_eWeaponAttributes' in shop_ui_weapon_stats:
            types = shop_ui_weapon_stats['m_eWeaponAttributes'].split(' | ')
            weapon_stats['WeaponTypes'] = ['Attribute_' + wtype for wtype in types]

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
        return last_y / ENGINE_UNITS_PER_METER
