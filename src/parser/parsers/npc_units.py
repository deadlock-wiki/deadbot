from loguru import logger
import utils.json_utils as json_utils
import utils.num_utils as num_utils


class NpcParser:
    """
    Parses the npc_units.vdata file to extract stats for various NPCs,
    including troopers, bosses, neutral units, and other game objects.
    """

    def __init__(self, npc_units_data, localizations):
        """
        Initializes the parser with necessary data.

        Args:
            npc_units_data (dict): The raw data from npc_units.vdata.
            localizations (dict): The localization data for mapping keys to names.
        """
        self.npc_units_data = npc_units_data
        self.localizations = localizations
        self.trooper_damage_reduction_from_objective = None
        self.NPC_PARSERS = {
            'trooper_normal': self._parse_trooper_ranged,
            'trooper_melee': self._parse_trooper_melee,
            'trooper_medic': self._parse_trooper_medic,
            'npc_boss_tier1': self._parse_guardian,
            'npc_barrack_boss': self._parse_base_guardian,
            'destroyable_building': self._parse_shrine,
            'npc_boss_tier2': self._parse_walker,
            'npc_boss_tier2_weak': self._parse_walker,
            'npc_boss_tier3': self._parse_patron,
            'neutral_trooper_weak': self._parse_neutral_trooper,
            'neutral_trooper_normal': self._parse_neutral_trooper,
            'neutral_trooper_strong': self._parse_neutral_trooper,
            'npc_super_neutral': self._parse_midboss,
            'neutral_sinners_sacrifice': self._parse_sinners_sacrifice,
            'citadel_item_pickup_rejuv': self._parse_rejuvenator,
        }

    def run(self, strict=True):
        """
        The main execution method. Iterates through all known NPC keys
        and parses their data, returning a consolidated dictionary.
        """
        # Pre-parse values that affect other units, like trooper damage reduction from objectives.
        barrack_boss_data = self.npc_units_data.get('npc_barrack_boss', {})
        self.trooper_damage_reduction_from_objective = self._read_value(
            barrack_boss_data, 'm_EnemyTrooperDamageReduction', 'm_flDamageReductionForTroopers'
        )

        all_npcs = {}
        for key in self.NPC_PARSERS.keys():
            if key not in self.npc_units_data:
                logger.warning(f"NPC key '{key}' not found in npc_units_data. Skipping.")
                continue

            npc_data = self.npc_units_data[key]
            try:
                parser_method = self.NPC_PARSERS[key]
                parsed_data = parser_method(npc_data)
                parsed_data['Name'] = self.localizations.get(key, key)
                all_npcs[key] = json_utils.sort_dict(parsed_data)
            except Exception as e:
                logger.error(f"Failed to parse NPC '{key}': {e}")
                if strict:
                    raise e
        return all_npcs

    # --- Helper Methods ---

    def _deep_get(self, data, *keys):
        """Safely access nested dictionary keys."""
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return None
            data = data[key]
        return data

    def _read_value(self, data, *keys):
        """Combines deep_get and assert_number for cleaner parsing."""
        value = self._deep_get(data, *keys)
        return num_utils.assert_number(value)

    def _parse_intrinsic_modifiers(self, data):
        """
        Parses intrinsic modifiers from the 'm_vecIntrinsicModifiers' list,
        shared by several NPC types.
        """
        intrinsics = {}
        if 'm_vecIntrinsicModifiers' not in data:
            return intrinsics

        # A map to convert raw modifier keys to friendly output keys.
        MODIFIER_MAP = {
            'MODIFIER_VALUE_BULLET_DAMAGE_REDUCTION_PERCENT': 'IntrinsicBulletResistance',
            'MODIFIER_VALUE_ABILITY_DAMAGE_REDUCTION_PERCENT': 'IntrinsicAbilityResistance',
            'MODIFIER_VALUE_HEALTH_REGEN_PER_SECOND': 'HealthRegenPerSecond',
        }

        for modifier in data['m_vecIntrinsicModifiers']:
            if 'm_vecScriptValues' in modifier:
                for script_value in modifier['m_vecScriptValues']:
                    if not isinstance(script_value, dict):
                        continue
                    
                    modifier_name = script_value.get('m_eModifierValue')
                    if modifier_name in MODIFIER_MAP:
                        output_key = MODIFIER_MAP[modifier_name]
                        intrinsics[output_key] = num_utils.assert_number(
                            script_value.get('m_value')
                        )
        return intrinsics

    # --- Trooper Parsers ---

    def _parse_trooper_shared(self, data):
        """Parses stats that are common to all trooper types."""
        stats = {
            'MaxHealth': self._read_value(data, 'm_nMaxHealth'),
            'PlayerDPS': self._read_value(data, 'm_flPlayerDPS'),
            'TrooperDPS': self._read_value(data, 'm_flTrooperDPS'),
            'T1BossDPS': self._read_value(data, 'm_flT1BossDPS'),
            'BarrackBossDPS': self._read_value(data, 'm_flBarrackBossDPS'),
            'SightRangePlayers': self._read_value(data, 'm_flSightRangePlayers'),
            'RunSpeed': self._read_value(data, 'm_flRunSpeed'),
            'DamageReductionNearEnemyBase': self.trooper_damage_reduction_from_objective,
        }
        return stats

    def _parse_trooper_ranged(self, data):
        return self._parse_trooper_shared(data)

    def _parse_trooper_medic(self, data):
        return self._parse_trooper_shared(data)

    def _parse_trooper_melee(self, data):
        stats = self._parse_trooper_shared(data)
        stats.update(
            {
                'MeleeDamage': self._read_value(data, 'm_flMeleeDamage'),
                'MeleeAttemptRange': self._read_value(data, 'm_flMeleeAttemptRange'),
            }
        )
        return stats

    # --- Objective & Boss Parsers ---

    def _parse_guardian(self, data):
        stats = {
            'MaxHealth': self._read_value(data, 'm_nMaxHealth'),
            'PlayerDPS': self._read_value(data, 'm_flPlayerDPS'),
            'TrooperDPS': self._read_value(data, 'm_flTrooperDPS'),
            'MeleeDamage': self._read_value(data, 'm_flMeleeDamage'),
            'MeleeAttemptRange': self._read_value(data, 'm_flMeleeAttemptRange'),
            'InvulnerabilityRange': self._read_value(data, 'm_flInvulRange'),
            'PlayerDamageResistance': self._read_value(data, 'm_flPlayerDamageResistPct'),
            'TrooperDamageResistanceBase': self._read_value(data, 'm_flT1BossDPSBaseResist'),
            'TrooperDamageResistanceMax': self._read_value(data, 'm_flT1BossDPSMaxResist'),
            'TrooperDamageResistanceRampUpTime': self._read_value(
                data, 'm_flT1BossDPSMaxResistTimeInSeconds'
            ),
        }
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_base_guardian(self, data):
        stats = self._parse_guardian(data)
        stats.update(
            {
                # Backdoor protection modifier provides damage mitigation and health regen.
                'BackdoorHealthRegen': self._read_value(
                    data, 'm_BackdoorProtectionModifier', 'm_flHealthPerSecondRegen'
                ),
                'BackdoorPlayerDamageMitigation': self._read_value(
                    data,
                    'm_BackdoorProtectionModifier',
                    'm_flBackdoorProtectionDamageMitigationFromPlayers',
                ),
                # Bullet resist modifier reduces damage based on nearby enemy heroes.
                'BackdoorBulletResistBase': self._read_value(
                    data, 'm_BackdoorBulletResistModifier', 'm_BulletResist'
                ),
                'BackdoorBulletResistReductionPerHero': self._read_value(
                    data,
                    'm_BackdoorBulletResistModifier',
                    'm_BulletResistReductionPerHero',
                ),
            }
        )
        return stats

    def _parse_shrine(self, data):
        return {
            'MaxHealth': self._read_value(data, 'm_iMaxHealthGenerator'),
            'AntiSnipeRange': self._read_value(
                data, 'm_RangedArmorModifier', 'm_flInvulnRange'
            ),
            'BulletResistBase': self._read_value(
                data, 'm_BackdoorBulletResistModifier', 'm_BulletResist'
            ),
            'BulletResistReductionPerHero': self._read_value(
                data, 'm_BackdoorBulletResistModifier', 'm_BulletResistReductionPerHero'
            ),
        }

    def _parse_walker(self, data):
        invuln_range = self._read_value(data, 'm_flInvulModifierRange')
        if invuln_range is None:
            invuln_range = self._read_value(data, 'm_flInvulRange')

        stats = {
            'MaxHealth': self._read_value(data, 'm_nMaxHealth'),
            'MeleeAttemptRange': self._read_value(data, 'm_flMeleeAttemptRange'),
            'SightRangePlayers': self._read_value(data, 'm_flSightRangePlayers'),
            'SightRangeNPCs': self._read_value(data, 'm_flSightRangeNPCs'),
            'PlayerInitialSightRange': self._read_value(data, 'm_flPlayerInitialSightRange'),
            'StompDamage': self._read_value(data, 'm_flStompDamage'),
            'StompDamageMaxHealthPercent': self._read_value(
                data, 'm_flStompDamageMaxHealthPercent'
            ),
            'StompRadius': self._read_value(data, 'm_flStompImpactRadius'),
            'StompStunDuration': self._read_value(data, 'm_flStunDuration'),
            'StompKnockup': self._read_value(data, 'm_flStompTossUpMagnitude'),
            'InvulnerabilityRange': invuln_range,
            'BoundAbilities': self._deep_get(data, 'm_mapBoundAbilities'),
            'FriendlyAuraRadius': self._read_value(
                data, 'm_FriendlyAuraModifier', 'm_flAuraRadius'
            ),
            'NearbyEnemyResistanceRange': self._read_value(
                data, 'm_NearbyEnemyResist', 'm_flNearbyEnemyResistRange'
            ),
            'NearbyEnemyResistanceValues': self._deep_get(
                data, 'm_NearbyEnemyResist', 'm_flResistValues'
            ),
            'RangedResistanceMaxValue': self._read_value(
                data, 'm_RangedArmorModifier', 'm_flBulletResistancePctMax'
            ),
            'RangedResistanceMinRange': self._read_value(
                data, 'm_RangedArmorModifier', 'm_flRangeMin'
            ),
            'RangedResistanceMaxRange': self._read_value(
                data, 'm_RangedArmorModifier', 'm_flRangeMax'
            ),
            'BackdoorHealthRegen': self._read_value(
                data, 'm_BackdoorProtectionModifier', 'm_flHealthPerSecondRegen'
            ),
            'BackdoorPlayerDamageMitigation': self._read_value(
                data,
                'm_BackdoorProtectionModifier',
                'm_flBackdoorProtectionDamageMitigationFromPlayers',
            ),
        }
        stats.update(self._parse_intrinsic_modifiers(data))

        # Parse friendly aura bonuses from the nested script values list using a data-driven map.
        AURA_MODIFIER_MAP = {
            'MODIFIER_VALUE_TECH_ARMOR_DAMAGE_RESIST': 'FriendlyAuraSpiritArmor',
            'MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST': 'FriendlyAuraBulletArmor',
        }
        
        # Initialize keys to null.
        for key in AURA_MODIFIER_MAP.values():
            stats[key] = None

        script_values = self._deep_get(
            data, 'm_FriendlyAuraModifier', 'm_modifierProvidedByAura', 'm_vecScriptValues'
        )

        if script_values and isinstance(script_values, list):
            for script_value in script_values:
                if isinstance(script_value, dict):
                    modifier_name = script_value.get('m_eModifierValue')
                    if modifier_name in AURA_MODIFIER_MAP:
                        output_key = AURA_MODIFIER_MAP[modifier_name]
                        stats[output_key] = num_utils.assert_number(script_value.get('m_value'))

        return stats

    def _parse_patron(self, data):
        stats = {
            'MaxHealthPhase1': self._read_value(data, 'm_nMaxHealth'),
            'MaxHealthPhase2': self._read_value(data, 'm_nPhase2Health'),
            'SightRangePlayers': self._read_value(data, 'm_flSightRangePlayers'),
            'LaserDPSToPlayers': self._read_value(data, 'm_flLaserDPSToPlayers'),
            'LaserDPSToNPCs': self._read_value(data, 'm_flLaserDPSToNPCs'),
            'LaserDPSMaxHealthPercent': self._read_value(data, 'm_flLaserDPSMaxHealth'),
            'IsUnkillableInPhase1': 'm_Phase1Modifier' in data,
            'HealthGrowthPerMinutePhase1': self._read_value(
                data, 'm_ObjectiveHealthGrowthPhase1', 'm_iGrowthPerMinute'
            ),
            'HealthGrowthPerMinutePhase2': self._read_value(
                data, 'm_ObjectiveHealthGrowthPhase2', 'm_iGrowthPerMinute'
            ),
            'OutOfCombatHealthRegen': self._read_value(
                data, 'm_ObjectiveRegen', 'm_flOutOfCombatHealthRegen'
            ),
            'RangedResistanceMinRange': self._read_value(
                data, 'm_RangedArmorModifier', 'm_flRangeMin'
            ),
            'RangedResistanceMaxRange': self._read_value(
                data, 'm_RangedArmorModifier', 'm_flRangeMax'
            ),
            'BackdoorHealthRegen': self._read_value(
                data, 'm_BackdoorProtection', 'm_flHealthPerSecondRegen'
            ),
            'BackdoorPlayerDamageMitigation': self._read_value(
                data,
                'm_BackdoorProtection',
                'm_flBackdoorProtectionDamageMitigationFromPlayers',
            ),
        }
        return stats

    # --- Neutral Unit Parsers ---

    def _parse_neutral_trooper(self, data):
        """Parses Neutral Troopers (weak, normal, strong)."""
        stats = {
            'MaxHealth': self._read_value(data, 'm_nMaxHealth'),
            'GoldReward': self._read_value(data, 'm_flGoldReward'),
            'GoldRewardBonusPercentPerMinute': self._read_value(
                data, 'm_flGoldRewardBonusPercentPerMinute'
            ),
        }
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_midboss(self, data):
        """Parses the Midboss (npc_super_neutral)."""
        stats = {
            'StartingHealth': self._read_value(data, 'm_iStartingHealth'),
            'HealthGainPerMinute': self._read_value(data, 'm_iHealthGainPerMinute'),
        }
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_sinners_sacrifice(self, data):
        """Parses Sinner's Sacrifice (neutral_vault)."""
        return {
            'RetaliateDamage': self._read_value(data, 'm_flRetaliateDamage'),
            'GoldReward': self._read_value(data, 'm_flGoldReward'),
            'GoldRewardBonusPercentPerMinute': self._read_value(
                data, 'm_flGoldRewardBonusPercentPerMinute'
            ),
        }

    # --- Item & Object Parsers ---

    def _parse_rejuvenator(self, data):
        """Parses the Rejuvenator pickup (citadel_item_pickup_rejuv)."""
        # Define constants for the script values array to avoid magic numbers.
        # The order is based on observation of the game data.
        REJUV_HEALTH_INDEX = 0
        REJUV_FIRERATE_INDEX = 1
        REJUV_SPIRIT_DMG_INDEX = 2

        stats = {}
        rebirth_data = self._deep_get(data, 'm_RebirthModifier')
        if rebirth_data:
            stats['RespawnDelay'] = num_utils.assert_number(
                rebirth_data.get('m_flRespawnDelay')
            )
            script_values = rebirth_data.get('m_vecScriptValues')

            if script_values and isinstance(script_values, list) and len(script_values) >= 3:
                stats['BonusMaxHealth'] = num_utils.assert_number(
                    script_values[REJUV_HEALTH_INDEX].get('m_value')
                )
                stats['BonusFireRate'] = num_utils.assert_number(
                    script_values[REJUV_FIRERATE_INDEX].get('m_value')
                )
                stats['BonusSpiritDamage'] = num_utils.assert_number(
                    script_values[REJUV_SPIRIT_DMG_INDEX].get('m_value')
                )
        return stats