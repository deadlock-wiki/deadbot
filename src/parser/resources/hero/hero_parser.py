import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import maps as maps
import utils.json_utils as json_utils
from ..constants import ENGINE_UNITS_PER_METER
from ..ability.ability_objects import Ability
from ..attribute.attribute_objects import Attribute
from ..hero.hero_objects import Hero


class HeroParser:
    def __init__(self, hero_data, abilities_data, localizations):
        self.hero_data = hero_data
        self.abilities_data = abilities_data
        Ability.load_objects()
        self.parsed_abilities = Ability.objects
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
                    'InDevelopment': hero_value['m_bInDevelopment'],
                    'IsDisabled': hero_value['m_bDisabled'],
                }

                hero_stats.update(
                    self._map_attr_names(hero_value['m_mapStartingStats'], maps.get_hero_attr)
                )

                # Change formatting on some numbers to match whats shown in game
                hero_stats['StaminaCooldown'] = 1 / hero_stats['StaminaRegenPerSecond']
                hero_stats['CritDamageReceivedScale'] = (
                    hero_stats['CritDamageReceivedScale'] - 1
                ) * 100
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

                # Parse DPS and Sustained DPS level scaling
                if 'DPS' in weapon_stats:
                    dps_stats = self._get_dps_stats(weapon_stats)
                    scaling_containers = ['LevelScaling', 'SpiritScaling']
                    dps_types = ['burst', 'sustained']
                    dps_types_localized = ['DPS', 'SustainedDPS']

                    for scaling_container in scaling_containers:
                        for dps_type, dps_type_localized in zip(dps_types, dps_types_localized):
                            dps_scaling = self._calc_dps_scaling(
                                dps_stats, hero_stats[scaling_container], dps_type
                            )

                            if dps_scaling != 0.0:
                                hero_stats[scaling_container][dps_type_localized] = dps_scaling

                hero_stats['WeaponName'] = 'citadel_weapon_' + hero_key + '_set'
                # i.e. citadel_weapon_hero_kelvin_set
                hero_stats['WeaponDescription'] = hero_stats['WeaponName'] + '_desc'

                all_hero_stats[hero_key] = json_utils.sort_dict(hero_stats)

        # Write meaningful stats to json file
        meaningful_stats = self._get_meaningful_stats(all_hero_stats)

        Hero.hash_to_objs(all_hero_stats)
        Hero.save_objects()
        Attribute.meaningful_stats = meaningful_stats
        Attribute.save_meaningful_stats()

        return all_hero_stats, meaningful_stats

    def _get_meaningful_stats(self, all_hero_stats):
        """
        Gets list of meaningful stats that are non-constant stats.

        Returns meaningful_stats dict

        Meaningful stats are ones that are either scaled by level/power increase,
        or have differing base values across the hero pool

        These are displayed on the deadlocked.wiki/Hero_Comparison page, among others in the future.
        """
        # Storing in dict with bool entry instead of list so its hashable on the frontend

        heroes_data = all_hero_stats.copy()
        stats_previous_value = {}
        meaningful_stats = {}

        # Iterate heroes
        for hero_key, hero_data in heroes_data.items():
            # Iterate hero stats
            for stat_key, stat_value in hero_data.items():
                # Must not be a container type, nor a bool
                if isinstance(stat_value, dict) or isinstance(stat_value, list):
                    continue

                # Ensure the data isn't a localization key
                if isinstance(stat_value, str) and (
                    any(str_to_match in stat_value for str_to_match in ['hero_', 'weapon_'])
                    or stat_key == 'Name'
                ):
                    continue

                # Add the stat's value to the dict
                if stat_key not in stats_previous_value:
                    stats_previous_value[stat_key] = stat_value

                # If its already tracked, and is different to current value, mark as meaningful
                else:
                    if stats_previous_value[stat_key] != stat_value:
                        meaningful_stats[stat_key] = True

            # If it has any scaling stats, mark them as meaningful
            scaling_containers = ['LevelScaling', 'SpiritScaling']
            for scaling_container in scaling_containers:
                if scaling_container in hero_data:
                    for level_key in hero_data[scaling_container].keys():
                        meaningful_stats[level_key] = True

        return meaningful_stats

    def _parse_hero_abilities(self, hero_value):
        bound_abilities = hero_value['m_mapBoundAbilities']

        abilities = {}
        for ability_position, bound_ability_key in bound_abilities.items():
            # ignore any abilities without any parsed data
            if bound_ability_key not in self.parsed_abilities.keys():
                continue
            abilities[ability_position] = self.parsed_abilities[bound_ability_key].data

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
            'BulletsPerShot': w['m_iBullets'],
            #'BulletRadius': w['m_flBulletRadius'] / ENGINE_UNITS_PER_METER,
        }

        dps_stats = self._get_dps_stats(weapon_stats)

        weapon_stats['DPS'] = self._calc_dps(dps_stats, 'burst')
        weapon_stats['SustainedDPS'] = self._calc_dps(dps_stats, 'sustained')

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

    def _get_dps_stats(self, weapon_stats):
        """Returns a dictionary of stats used to calculate DPS"""
        # TODO: These should be grouped under a "Weapon" key in hero data, among other things
        return {
            'ReloadSingle': weapon_stats['ReloadSingle'],
            'ReloadDelay': weapon_stats['ReloadDelay'],
            'ReloadTime': weapon_stats['ReloadTime'],
            'ClipSize': weapon_stats['ClipSize'],
            'RoundsPerSecond': weapon_stats['RoundsPerSecond'],
            'BulletDamage': weapon_stats['BulletDamage'],
            'BulletsPerShot': weapon_stats['BulletsPerShot'],
        }

    def _calc_dps(self, dps_stats, type='burst'):
        """Calculates Burst or Sustained DPS of a weapon"""

        # All reload actions have ReloadDelay played first,
        # but typically only single bullet reloads have a non-zero delay
        # i.e.
        # ReloadDelay of .5,
        # ReloadTime of 1,
        # ClipSize of 10,
        # =time to reload 1 bullet is 1.5s, time to reload 10 bullets is 10.5s

        # Abbreivated dictionary for easier access
        d = dps_stats.copy()

        if type == 'burst':
            return d['BulletDamage'] * d['RoundsPerSecond'] * d['BulletsPerShot']

        elif type == 'sustained':
            if d['ReloadSingle']:
                # If reloading 1 bullet at a time, reload time is actually per bullet
                time_to_reload = d['ReloadTime'] * d['ClipSize']
            else:
                time_to_reload = d['ReloadTime']
            time_to_reload += d['ReloadDelay']
            time_to_empty_clip = d['ClipSize'] / d['RoundsPerSecond']
            # More bullets per shot doesn't consume more bullets in the clip,
            # so think of it as bullet per bullet
            damage_from_clip = d['BulletDamage'] * d['BulletsPerShot'] * d['ClipSize']
            return damage_from_clip / (time_to_empty_clip + time_to_reload)

        else:
            raise Exception('Invalid DPS type, must be one of: ' + ', '.join(['burst', 'sustained']))

    def _calc_dps_scaling(self, dps_stats_, scalings, type='burst'):
        """
        Calc DPS level/spirit scaling based on the scalars.

        i.e. with bullet dmg scaling
        Dps scaling = dps * bullet dmg scaling / bullet dmg
        """
        # Scalars i.e content of SpiritScaling
        # Mostly so it can be displayed on deadlocked.wiki/Hero_Comparison
        dps_stats = dps_stats_.copy()
        dps_stats_scaled = dps_stats_.copy()

        # Increase all stats by the scalar
        for scalar_key, scalar_value in scalings.items():
            if scalar_key in dps_stats_scaled:
                dps_stats_scaled[scalar_key] += scalar_value

        # unscaled_dps = self._calc_dps(dps_stats_, type)
        scaled_dps = self._calc_dps(dps_stats_scaled, type)
        dps = self._calc_dps(dps_stats, type)

        return scaled_dps - dps

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
