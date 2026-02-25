import copy
import parser.maps as maps
import utils.json_utils as json_utils
from utils.num_utils import round_sig_figs
from . import weapon_parser


class HeroParser:
    def __init__(self, hero_data, abilities_data, parsed_abilities, localizations):
        self.hero_data = hero_data
        self.abilities_data = abilities_data
        self.parsed_abilities = parsed_abilities
        self.localizations = localizations

        # Manually add localization for transformed Silver
        base_name = self.localizations.get('hero_werewolf')
        if base_name:
            self.localizations['hero_werewolf_transformed'] = f'{base_name} (Transformed)'

        # Ability 4 on werewolf changes abilities 1, 2 and 3. So we will instead create a duplicate hero with its own key
        # in order to maintain the format of a hero having 4 abilities
        self.hero_data['hero_werewolf_transformed'] = self._create_werewolf_transformed()

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

                # Calculate dash speeds (distance / duration)
                if 'GroundDashDistanceInMeters' in hero_stats and 'GroundDashDuration' in hero_stats:
                    hero_stats['GroundDashSpeed'] = round_sig_figs(hero_stats['GroundDashDistanceInMeters'] / hero_stats['GroundDashDuration'], 3)

                if 'AirDashDistanceInMeters' in hero_stats and 'AirDashDuration' in hero_stats:
                    hero_stats['AirDashSpeed'] = round_sig_figs(hero_stats['AirDashDistanceInMeters'] / hero_stats['AirDashDuration'], 3)

                # Convert scale values to percentages and rename keys for clarity
                received_scale = hero_stats.pop('CritDamageReceivedScale')
                hero_stats['CritDamageReceivedPercent'] = round_sig_figs((1 - received_scale) * 100, 5)

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
                    dps_stats = weapon_parser.get_dps_calculation_stats(hero_stats['Weapon'])
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

    def _create_werewolf_transformed(self):
        """Create a copy hero_werewolf data and modify its bound abilities to use the transformed abilities and weapon"""
        werewolf: dict = self.hero_data['hero_werewolf']
        werewolf_transformed: dict = copy.deepcopy(werewolf)

        # Werewolf claws use alt-fire scaling as their base bullet damage modifier
        if 'm_mapStandardLevelUpUpgrades' in werewolf_transformed:
            upgrades = werewolf_transformed['m_mapStandardLevelUpUpgrades']
            if 'MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL_ALT_FIRE' in upgrades:
                # Werewolf claws use alt-fire scaling as their primary damage scaling
                upgrades['MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL'] = upgrades['MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL_ALT_FIRE']
                # Remove the alt-fire key to keep the data clean
                del upgrades['MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL_ALT_FIRE']

        # Treat claws as having no ammo limit (continuous attacks during transformation)
        claws_id = 'citadel_weapon_werewolf_claws'
        if claws_id in self.abilities_data and 'm_WeaponInfo' in self.abilities_data[claws_id]:
            self.abilities_data[claws_id]['m_WeaponInfo']['m_iClipSize'] = 0

        transformation_ability = self.abilities_data['ability_werewolf_transformation']
        modifier = transformation_ability['m_WerewolfModifier']

        for key in werewolf_transformed['m_mapBoundAbilities']:
            new_ability = modifier['m_mapWerewolfAbilities'].get(key)
            if new_ability:
                werewolf_transformed['m_mapBoundAbilities'][key] = new_ability

        return werewolf_transformed

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

            # ignore anything that isn't a standard ability slot
            if ability_position not in ['ESlot_Signature_1', 'ESlot_Signature_2', 'ESlot_Signature_3', 'ESlot_Signature_4']:
                continue

            abilities[ability_position] = self.parsed_abilities[bound_ability_key]
        return self._map_attr_names(abilities, maps.get_bound_abilities)

    def _parse_weapon_stats(self, weapon_info):
        """
        Parses a 'm_WeaponInfo' block for a primary or alternate fire mode.
        Returns a dictionary of parsed weapon stats.
        """
        return weapon_parser.parse_weapon_info(weapon_info)

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
                    alt_dps_stats = weapon_parser.get_dps_calculation_stats(alt_stats)
                    if alt_dps_stats.get('RoundsPerSecond', 0) > 0:
                        alt_stats['DPS'] = round_sig_figs(weapon_parser.calculate_dps(alt_dps_stats, 'burst'), 5)
                        alt_stats['SustainedDPS'] = round_sig_figs(weapon_parser.calculate_dps(alt_dps_stats, 'sustained'), 5)

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

        scaled_dps = weapon_parser.calculate_dps(dps_stats_scaled, type)
        dps = weapon_parser.calculate_dps(dps_stats, type)

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
