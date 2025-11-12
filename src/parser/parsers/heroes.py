import parser.maps as maps
import utils.json_utils as json_utils
from utils.num_utils import convert_engine_units_to_meters, round_sig_figs


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
                    'InDevelopment': hero_value['m_bInDevelopment'],
                    'IsDisabled': hero_value['m_bDisabled'],
                    'IsRecommended': hero_value.get('m_bNewPlayerRecommended', False),
                    'InHeroLabs': hero_value.get('m_bAvailableInHeroLabs', False),
                    'IsSelectable': hero_value.get('m_bPlayerSelectable', True),
                    'Type': self._parse_hero_type(hero_value),
                }

                hero_stats.update(self._map_attr_names(hero_value['m_mapStartingStats'], maps.get_hero_attr))

                # Change formatting on some numbers to match whats shown in game
                hero_stats['StaminaCooldown'] = 1 / hero_stats['StaminaRegenPerSecond']

                # Convert scale values to percentages and rename keys for clarity
                received_scale = hero_stats.pop('CritDamageReceivedScale')
                hero_stats['CritDamageReceivedPercent'] = round_sig_figs((received_scale - 1) * 100, 5)

                bonus_scale = hero_stats.pop('CritDamageBonusScale')
                hero_stats['CritDamageBonusPercent'] = round_sig_figs((bonus_scale - 1) * 100, 5)

                hero_stats['TechRange'] = hero_stats['TechRange'] - 1
                hero_stats['TechDuration'] = hero_stats['TechDuration'] - 1
                hero_stats['ReloadSpeed'] = hero_stats['ReloadSpeed'] - 1

                hero_stats['SpiritScaling'] = self._parse_spirit_scaling(hero_value)

                # Parse weapon data and nest it under a 'Weapon' key
                weapon_data = self._parse_hero_weapon(hero_value, hero_key)
                if weapon_data:
                    hero_stats['Weapon'] = weapon_data

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

                        hero_stats['LevelScaling']['HeavyMeleeDamage'] = round_sig_figs(md_scalar * hl_ratio, 5)
                        del hero_stats['LevelScaling']['MeleeDamage']

                    # Remove scalings if they are 0.0
                    hero_stats['LevelScaling'] = {k: v for k, v in hero_stats['LevelScaling'].items() if v != 0.0}

                # Parse DPS and Sustained DPS level scaling
                if 'Weapon' in hero_stats and 'DPS' in hero_stats['Weapon']:
                    dps_stats = self._get_dps_stats(hero_stats['Weapon'])
                    scaling_containers = ['LevelScaling', 'SpiritScaling']
                    dps_types = ['burst', 'sustained']
                    dps_types_localized = ['DPS', 'SustainedDPS']

                    for scaling_container in scaling_containers:
                        for dps_type, dps_type_localized in zip(dps_types, dps_types_localized):
                            dps_scaling = self._calc_dps_scaling(dps_stats, hero_stats.get(scaling_container, {}), dps_type)

                            if dps_scaling != 0.0:
                                if scaling_container not in hero_stats:
                                    hero_stats[scaling_container] = {}
                                # We store the scaling at the top level, not in the weapon object
                                hero_stats[scaling_container][dps_type_localized] = round_sig_figs(dps_scaling, 5)

                if 'm_RecommendedUpgrades' in hero_value:
                    hero_stats['RecommendedItems'] = hero_value['m_RecommendedUpgrades']

                all_hero_stats[hero_key] = json_utils.sort_dict(hero_stats)

        # Write meaningful stats to json file
        meaningful_stats = self._get_meaningful_stats(all_hero_stats)

        return all_hero_stats, meaningful_stats

    def _get_meaningful_stats(self, all_hero_stats):
        """
        Gets list of meaningful stats that are non-constant stats.

        Returns meaningful_stats dict

        Meaningful stats are ones that are either scaled by level/power increase,
        or have differing base values across the hero pool

        These are displayed on the deadlock.wiki/Hero_Comparison page, among others in the future.
        """
        # Storing in dict with bool entry instead of list so its hashable on the frontend
        heroes_data = all_hero_stats.copy()
        stats_previous_value = {}
        meaningful_stats = {}

        # Iterate heroes
        for hero_key, hero_data in heroes_data.items():
            # Create a flattened version of the hero data for comparison
            flat_data = hero_data.copy()
            if 'Weapon' in flat_data:
                weapon_data = flat_data.pop('Weapon')
                flat_data.update(weapon_data)  # Add weapon stats to top level for comparison
                if 'AltFire' in weapon_data:
                    # For simplicity, we don't compare alt-fire stats in this function yet
                    flat_data.pop('AltFire')

            # Iterate hero stats
            for stat_key, stat_value in flat_data.items():
                # Must not be a container type, nor a bool
                if isinstance(stat_value, dict) or isinstance(stat_value, list):
                    continue

                # Ensure the data isn't a localization key
                if isinstance(stat_value, str) and (any(str_to_match in stat_value for str_to_match in ['hero_', 'weapon_']) or stat_key == 'Name'):
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

    def _parse_hero_type(self, hero_value):
        hero_type = hero_value.get('m_eHeroType')
        if hero_type is None:
            return None

        hero_type = hero_type.replace('ECitadelHeroType_', '')
        hero_localization_str = f'Citadel_HeroGrid_{hero_type}'

        # Get hero type from localization, but fallback to the raw value if not found
        return self.localizations.get(hero_localization_str, hero_type)

    def _parse_hero_abilities(self, hero_value):
        bound_abilities = hero_value['m_mapBoundAbilities']
        abilities = {}
        for ability_position, bound_ability_key in bound_abilities.items():
            # ignore any abilities without any parsed data
            if bound_ability_key not in self.parsed_abilities:
                continue
            abilities[ability_position] = self.parsed_abilities[bound_ability_key]
        return self._map_attr_names(abilities, maps.get_bound_abilities)

    def _parse_weapon_stats(self, weapon_info):
        """
        Parses a 'm_WeaponInfo' block for a primary or alternate fire mode.
        Returns a dictionary of parsed weapon stats.
        """
        stats = {}

        # Core Stats
        stats['BulletSpeed'] = convert_engine_units_to_meters(weapon_info.get('m_flBulletSpeed'))
        stats['BulletDamage'] = weapon_info.get('m_flBulletDamage', 0)
        stats['RoundsPerSecond'] = round_sig_figs(self._calc_rounds_per_sec(weapon_info), 5)
        stats['ClipSize'] = weapon_info.get('m_iClipSize')
        stats['ReloadTime'] = weapon_info.get('m_reloadDuration')
        stats['ReloadMovespeed'] = float(weapon_info.get('m_flReloadMoveSpeed', '0')) / 10000
        stats['ReloadDelay'] = weapon_info.get('m_flReloadSingleBulletsInitialDelay', 0)
        stats['ReloadSingle'] = weapon_info.get('m_bReloadSingleBullets', False)

        # Falloff and Range
        stats['FalloffStartRange'] = convert_engine_units_to_meters(weapon_info.get('m_flDamageFalloffStartRange', 0))
        stats['FalloffEndRange'] = convert_engine_units_to_meters(weapon_info.get('m_flDamageFalloffEndRange', 0))
        stats['FalloffStartScale'] = weapon_info.get('m_flDamageFalloffStartScale', 1.0)
        stats['FalloffEndScale'] = weapon_info.get('m_flDamageFalloffEndScale', 1.0)
        stats['FalloffBias'] = weapon_info.get('m_flDamageFalloffBias', 0.5)

        # Bullet Properties
        stats['BulletGravityScale'] = weapon_info.get('m_flBulletGravityScale', 0)
        stats['BulletsPerShot'] = weapon_info.get('m_iBullets', 1)
        stats['BulletsPerBurst'] = weapon_info.get('m_iBurstShotCount', 1)
        stats['BurstInterShotInterval'] = weapon_info.get('m_flIntraBurstCycleTime', 0)
        stats['ShootMoveSpeed'] = weapon_info.get('m_flShootMoveSpeedPercent', 1.0)
        stats['HitOnceAcrossAllBullets'] = weapon_info.get('m_bHitOnceAcrossAllBullets', False)
        stats['CanCrit'] = weapon_info.get('m_bCanCrit', True)
        stats['AmmoConsumedPerShot'] = weapon_info.get('m_iAmmoConsumedPerShot', 1)

        # Explosive Properties (often for alt-fire)
        if 'm_flExplosionRadius' in weapon_info:
            stats['ExplosionRadius'] = convert_engine_units_to_meters(weapon_info['m_flExplosionRadius'])
        if 'm_flExplosionDamageScaleAtMaxRadius' in weapon_info:
            stats['ExplosionDamageScaleAtMaxRadius'] = weapon_info['m_flExplosionDamageScaleAtMaxRadius']

        # Spin-up Properties
        if weapon_info.get('m_bSpinsUp'):
            max_spin_cycle_time = weapon_info.get('m_flMaxSpinCycleTime')
            stats['RoundsPerSecondAtMaxSpin'] = 1 / max_spin_cycle_time if max_spin_cycle_time and max_spin_cycle_time > 0 else 0
            stats['SpinAcceleration'] = weapon_info.get('m_flSpinIncreaseRate', 0)
            stats['SpinDeceleration'] = weapon_info.get('m_flSpinDecayRate', 0)

        # Calculate DPS
        dps_stats = self._get_dps_stats(stats)
        if dps_stats.get('RoundsPerSecond', 0) > 0:
            stats['DPS'] = round_sig_figs(self._calc_dps(dps_stats, 'burst'), 5)
            stats['SustainedDPS'] = round_sig_figs(self._calc_dps(dps_stats, 'sustained'), 5)

        return stats

    def _parse_hero_weapon(self, hero_value, hero_key):
        weapon_stats = {}
        bound_abilities = hero_value['m_mapBoundAbilities']

        # Primary weapon
        primary_slot = 'ESlot_Weapon_Primary'
        if primary_slot in bound_abilities:
            weapon_prim_id = bound_abilities[primary_slot]
            if weapon_prim_id in self.abilities_data and 'm_WeaponInfo' in self.abilities_data[weapon_prim_id]:
                primary_ability_data = self.abilities_data[weapon_prim_id]
                weapon_stats = self._parse_weapon_stats(primary_ability_data['m_WeaponInfo'])

                # The primary weapon name/description key is constructed from the hero's key, not its own ability ID.
                # e.g., hero_shiv -> citadel_weapon_hero_shiv_set
                weapon_stats['NameKey'] = f"citadel_weapon_hero_{hero_key.replace('hero_', '')}_set"
                weapon_stats['DescKey'] = weapon_stats['NameKey'] + '_desc'

        # Alt-fire weapon
        # It's not in a special slot, but is an ability with a specific behavior flag.
        for slot, ability_id in bound_abilities.items():
            if slot == primary_slot:
                continue  # Skip the primary weapon we've already parsed

            ability_data = self.abilities_data.get(ability_id)
            if not ability_data:
                continue

            # Check if this ability is flagged as an alternative weapon
            if 'CITADEL_ABILITY_BEHAVIOR_IS_ALTERNATIVE_WEAPON' in ability_data.get('m_AbilityBehaviorsBits', ''):
                if 'm_WeaponInfo' in ability_data:
                    alt_stats = self._parse_weapon_stats(ability_data['m_WeaponInfo'])

                    # Inherit clip/reload stats from primary if missing for accurate DPS calculation
                    if alt_stats.get('ClipSize') is None:
                        alt_stats['ClipSize'] = weapon_stats.get('ClipSize')
                    if alt_stats.get('ReloadTime') is None:
                        alt_stats['ReloadTime'] = weapon_stats.get('ReloadTime')

                    # Recalculate DPS with inherited stats if needed
                    alt_dps_stats = self._get_dps_stats(alt_stats)
                    if alt_dps_stats.get('RoundsPerSecond', 0) > 0:
                        alt_stats['DPS'] = round_sig_figs(self._calc_dps(alt_dps_stats, 'burst'), 5)
                        alt_stats['SustainedDPS'] = round_sig_figs(self._calc_dps(alt_dps_stats, 'sustained'), 5)

                    # Alt-fire uses its own ability ID for its name and description key.
                    alt_stats['NameKey'] = ability_id
                    alt_stats['DescKey'] = f'{ability_id}_desc'
                    weapon_stats['AltFire'] = alt_stats
                    break  # Assume only one alt-fire per hero

        # Weapon Types (Tags)
        shop_ui_weapon_stats = hero_value['m_ShopStatDisplay']['m_eWeaponStatsDisplay']
        if 'm_eWeaponAttributes' in shop_ui_weapon_stats:
            types = shop_ui_weapon_stats['m_eWeaponAttributes'].split(' | ')
            weapon_stats['WeaponTypes'] = ['Attribute_' + wtype for wtype in types]

        return weapon_stats

    def _get_dps_stats(self, weapon_stats):
        """Returns a dictionary of stats used to calculate DPS"""
        return {
            'ReloadSingle': weapon_stats.get('ReloadSingle'),
            'ReloadDelay': weapon_stats.get('ReloadDelay'),
            'ReloadTime': weapon_stats.get('ReloadTime'),
            'ClipSize': weapon_stats.get('ClipSize'),
            'RoundsPerSecond': (
                weapon_stats.get('RoundsPerSecondAtMaxSpin')
                if 'SpinAcceleration' in weapon_stats and weapon_stats.get('RoundsPerSecondAtMaxSpin')
                else weapon_stats.get('RoundsPerSecond')
            ),
            'BurstInterShotInterval': weapon_stats.get('BurstInterShotInterval'),
            'BulletDamage': weapon_stats.get('BulletDamage'),
            'BulletsPerShot': weapon_stats.get('BulletsPerShot'),
            'BulletsPerBurst': weapon_stats.get('BulletsPerBurst'),
            'HitOnceAcrossAllBullets': weapon_stats.get('HitOnceAcrossAllBullets'),
        }

    def _calc_rounds_per_sec(self, weapon_info):
        """
        Calculates the rounds per second of a mouse click by dividing the total bullets per shot
        by the total shot time, taking consideration of the cooldown between shots during a burst
        """
        shot_cd = weapon_info.get('m_flCycleTime', 0)
        burst_cd = weapon_info.get('m_flBurstShotCooldown', 0)
        intra_burst_cd = weapon_info.get('m_flIntraBurstCycleTime', 0)
        bullets_per_shot = weapon_info.get('m_iBurstShotCount', 0)

        total_shot_time = bullets_per_shot * intra_burst_cd + shot_cd + burst_cd

        return bullets_per_shot / total_shot_time

    def _calc_dps(self, dps_stats, type='burst'):
        """Calculates Burst or Sustained DPS of a weapon"""
        # Burst, not to be confused with burst as in burst fire, but rather
        # a burst of damage where delta time is 0.
        # Sustained has a delta time of infinity, meaning it takes into
        # account time-to-empty-clip and reload time.
        stats = {k: v for k, v in dps_stats.items() if v is not None}

        if stats.get('RoundsPerSecond', 0) == 0:
            return 0

        # If damage is dealt once for all bullets (e.g. shotguns), treat as 1 bullet for DPS
        bullets_per_shot = 1 if stats.get('HitOnceAcrossAllBullets') else stats.get('BulletsPerShot', 1)
        cycle_time = 1 / stats['RoundsPerSecond']
        total_cycle_time = cycle_time * stats.get('BulletsPerBurst', 1)

        if total_cycle_time == 0:
            return 0

        # Burst DPS accounts for burst weapons and assumes maximum spinup (if applicable)
        if type == 'burst':
            dps = stats.get('BulletDamage', 0) * bullets_per_shot * stats.get('BulletsPerBurst', 1) / total_cycle_time
            return dps

        # Sustained DPS also accounts for reloads/clipsize
        elif type == 'sustained':
            clip_size = stats.get('ClipSize', 0)
            if clip_size == 0:
                # For weapons with no clip (like Bebop's beam), sustained DPS is the same as burst DPS
                sustained_dps = stats.get('BulletDamage', 0) * bullets_per_shot * stats.get('BulletsPerBurst', 1) / total_cycle_time
                return sustained_dps

            # All reload actions have ReloadDelay played first,
            # but typically only single bullet reloads have a non-zero delay
            if stats.get('ReloadSingle'):
                # If reloading 1 bullet at a time, reload time is actually per bullet
                time_to_reload = stats.get('ReloadTime', 0) * clip_size
            else:
                time_to_reload = stats.get('ReloadTime', 0)

            time_to_reload += stats.get('ReloadDelay', 0)
            time_to_empty_clip = clip_size / stats.get('BulletsPerBurst', 1) * total_cycle_time
            # BulletsPerShot doesn't consume more ammo, but BulletsPerBurst does.
            damage_from_clip = stats.get('BulletDamage', 0) * bullets_per_shot * clip_size

            total_time = time_to_empty_clip + time_to_reload
            if total_time == 0:
                return 0

            sustained_dps = damage_from_clip / total_time
            return sustained_dps

        else:
            raise Exception('Invalid DPS type, must be one of: ' + ', '.join(['burst', 'sustained']))

    def _calc_dps_scaling(self, dps_stats_, scalings, type='burst'):
        """
        Calc DPS level/spirit scaling based on the scalars.
        """
        dps_stats = dps_stats_.copy()
        dps_stats_scaled = dps_stats_.copy()

        # Increase all stats by the scalar
        for scalar_key, scalar_value in scalings.items():
            if scalar_key in dps_stats_scaled and dps_stats_scaled[scalar_key] is not None:
                dps_stats_scaled[scalar_key] += scalar_value

        scaled_dps = self._calc_dps(dps_stats_scaled, type)
        dps = self._calc_dps(dps_stats, type)

        return round_sig_figs(scaled_dps - dps, 5)

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
            parsed_spirit_scaling[maps.get_hero_attr(hero_scaling_key)] = hero_scaling_value['flScale']

            # Ensure the only scalar in here is ETechPower
            if 'ETechPower' != hero_scaling_value['eScalingStat']:
                raise Exception(f'Expected scaling key "ETechPower" but is: {hero_scaling_value["eScalingStat"]}')

        return parsed_spirit_scaling

    # maps all keys in an object using the provided function
    def _map_attr_names(self, data, func):
        output_data = dict()
        for key in data:
            mapped_key = func(key)
            output_data[mapped_key] = data[key]

        return output_data
