from loguru import logger
import utils.json_utils as json_utils
import utils.num_utils as num_utils
from utils.num_utils import convert_engine_units_to_meters
import parser.maps as maps


class NpcParser:
    """
    Parses the npc_units.vdata file to extract stats for various NPCs,
    including troopers, bosses, neutral units, and other game objects.
    """

    def __init__(self, npc_units_data, modifiers_data, misc_data, localizations, parsed_abilities):
        """
        Initializes the parser with necessary data.

        Args:
            npc_units_data (dict): The raw data from npc_units.vdata.
            modifiers_data (dict): The raw data from modifiers.vdata.
            misc_data (dict): The raw data from misc.vdata.
            localizations (dict): The localization data for mapping keys to names.
            parsed_abilities (dict): The pre-parsed ability data.
        """
        self.npc_units_data = npc_units_data
        self.modifiers_data = modifiers_data
        self.misc_data = misc_data
        self.localizations = localizations
        self.parsed_abilities = parsed_abilities
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
        self.trooper_damage_reduction_from_objective = json_utils.read_value(
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
                parsed_data = parser_method(npc_data, key)
                parsed_data['Name'] = self.localizations.get(key, key)
                all_npcs[key] = json_utils.sort_dict(parsed_data)
            except Exception as e:
                logger.error(f"Failed to parse NPC '{key}': {e}")
                if strict:
                    raise e
        return all_npcs

    # --- Helper Methods ---

    def _parse_npc_abilities(self, raw_abilities):
        """
        Parses the raw m_mapBoundAbilities dictionary by looking up ability
        details in the pre-parsed abilities dictionary.
        """
        if not isinstance(raw_abilities, dict):
            return None

        formatted_abilities = {}
        for slot, ability_key in raw_abilities.items():
            slot_number = slot.split('_')[-1]
            if not slot_number.isdigit() or ability_key not in self.parsed_abilities:
                continue

            ability_data = self.parsed_abilities[ability_key]
            formatted_abilities[slot_number] = {'Name': ability_data['Name'], 'Key': ability_key}

        return formatted_abilities if formatted_abilities else None

    def _parse_intrinsic_modifiers(self, data):
        """
        Parses intrinsic modifiers from the 'm_vecIntrinsicModifiers' list,
        shared by several NPC types.
        """
        intrinsics = {}
        intrinsic_modifiers = data.get('m_vecIntrinsicModifiers')
        if not isinstance(intrinsic_modifiers, list):
            return intrinsics

        for modifier in intrinsic_modifiers:
            script_values = modifier.get('m_vecScriptValues')
            if not isinstance(script_values, list):
                continue

            for script_value in script_values:
                if not isinstance(script_value, dict):
                    continue

                modifier_name = script_value.get('m_eModifierValue')
                output_key = maps.get_npc_intrinsic_modifier(modifier_name)
                if output_key:
                    intrinsics[output_key] = num_utils.assert_number(script_value.get('m_value'))
        return intrinsics

    def _parse_spawn_info(self, npc_key):
        """
        Parses initial spawn delay and respawn interval from misc_data.
        Maps the npc_key (e.g., 'neutral_trooper_weak') to the corresponding
        key in misc_data (e.g., 'neutral_camp_weak').
        """
        spawn_info = {}
        # This map connects the npc_units key to the misc_data key
        SPAWNER_MAP = {
            'neutral_trooper_weak': 'neutral_camp_weak',
            'neutral_trooper_normal': 'neutral_camp_medium',
            'neutral_trooper_strong': 'neutral_camp_strong',
            'npc_super_neutral': 'neutral_camp_midboss',
            'neutral_sinners_sacrifice': 'neutral_camp_vaults',
        }

        spawner_key = SPAWNER_MAP.get(npc_key)
        if spawner_key and spawner_key in self.misc_data:
            spawner_data = self.misc_data[spawner_key]
            spawn_info['InitialSpawnDelay'] = json_utils.read_value(spawner_data, 'm_iInitialSpawnDelayInSeconds')
            spawn_info['SpawnInterval'] = json_utils.read_value(spawner_data, 'm_iSpawnIntervalInSeconds')

        return spawn_info

    def _parse_backdoor_protection(self, data, key='m_BackdoorProtectionModifier'):
        """Parses common backdoor protection stats."""
        return {
            'BackdoorHealthRegen': json_utils.read_value(data, key, 'm_flHealthPerSecondRegen'),
            'BackdoorPlayerDamageMitigation': json_utils.read_value(data, key, 'm_flBackdoorProtectionDamageMitigationFromPlayers'),
        }

    def _parse_ranged_resistance(self, data):
        """Parses ranged armor modifier stats."""
        return {
            'RangedResistanceMaxValue': json_utils.read_value(data, 'm_RangedArmorModifier', 'm_flBulletResistancePctMax'),
            'RangedResistanceMinRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_RangedArmorModifier', 'm_flRangeMin')),
            'RangedResistanceMaxRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_RangedArmorModifier', 'm_flRangeMax')),
        }

    # --- Trooper Parsers ---

    def _parse_trooper_shared(self, data, npc_key=None):
        """Parses stats that are common to all trooper types."""
        stats = {
            'MaxHealth': json_utils.read_value(data, 'm_nMaxHealth'),
            'PlayerDPS': json_utils.read_value(data, 'm_flPlayerDPS'),
            'TrooperDPS': json_utils.read_value(data, 'm_flTrooperDPS'),
            'T1BossDPS': json_utils.read_value(data, 'm_flT1BossDPS'),
            'BarrackBossDPS': json_utils.read_value(data, 'm_flBarrackBossDPS'),
            'SightRangePlayers': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangePlayers')),
            'SightRangeNPCs': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangeNPCs')),
            'RunSpeed': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flRunSpeed')),
            'WalkSpeed': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flWalkSpeed')),
            'WeaponRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_WeaponInfo', 'm_flRange')),
            'DamageReductionNearEnemyBase': self.trooper_damage_reduction_from_objective,
            # Resistances
            'PlayerDamageResistance': json_utils.read_value(data, 'm_flPlayerDamageResistPct'),
            'TrooperDamageResistance': json_utils.read_value(data, 'm_flTrooperDamageResistPct'),
            'T2BossDamageResistance': json_utils.read_value(data, 'm_flT2BossDamageResistPct'),
            'T3BossDamageResistance': json_utils.read_value(data, 'm_flT3BossDamageResistPct'),
        }
        return stats

    def _parse_trooper_ranged(self, data, npc_key=None):
        return self._parse_trooper_shared(data, npc_key)

    def _parse_trooper_medic(self, data, npc_key=None):
        stats = self._parse_trooper_shared(data, npc_key)
        stats['BoundAbilities'] = self._parse_npc_abilities(data.get('m_mapBoundAbilities'))
        return stats

    def _parse_trooper_melee(self, data, npc_key=None):
        stats = self._parse_trooper_shared(data, npc_key)
        stats.update(
            {
                'MeleeDamage': json_utils.read_value(data, 'm_flMeleeDamage'),
                'MeleeAttemptRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flMeleeAttemptRange')),
            }
        )
        return stats

    # --- Objective & Boss Parsers ---

    def _parse_guardian(self, data, npc_key=None):
        stats = {
            'MaxHealth': json_utils.read_value(data, 'm_nMaxHealth'),
            'PlayerDPS': json_utils.read_value(data, 'm_flPlayerDPS'),
            'TrooperDPS': json_utils.read_value(data, 'm_flTrooperDPS'),
            'MeleeDamage': json_utils.read_value(data, 'm_flMeleeDamage'),
            'MeleeAttemptRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flMeleeAttemptRange')),
            'SightRangePlayers': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangePlayers')),
            'SightRangeNPCs': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangeNPCs')),
            'InvulnerabilityRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flInvulRange')),
            'PlayerDamageResistance': json_utils.read_value(data, 'm_flPlayerDamageResistPct'),
            'TrooperDamageResistanceBase': json_utils.read_value(data, 'm_flT1BossDPSBaseResist'),
            'TrooperDamageResistanceMax': json_utils.read_value(data, 'm_flT1BossDPSMaxResist'),
            'TrooperDamageResistanceRampUpTime': json_utils.read_value(data, 'm_flT1BossDPSMaxResistTimeInSeconds'),
        }
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_base_guardian(self, data, npc_key=None):
        stats = self._parse_guardian(data, npc_key)
        stats.update(self._parse_backdoor_protection(data))
        stats.update(
            {
                # Bullet resist modifier reduces damage based on nearby enemy heroes.
                'BackdoorBulletResistBase': json_utils.read_value(data, 'm_BackdoorBulletResistModifier', 'm_BulletResist'),
                'BackdoorBulletResistReductionPerHero': json_utils.read_value(
                    data,
                    'm_BackdoorBulletResistModifier',
                    'm_BulletResistReductionPerHero',
                ),
            }
        )
        return stats

    def _parse_shrine(self, data, npc_key=None):
        stats = {
            'MaxHealth': json_utils.read_value(data, 'm_iMaxHealthGenerator'),
            'AntiSnipeRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_RangedArmorModifier', 'm_flInvulnRange')),
            'BulletResistBase': json_utils.read_value(data, 'm_BackdoorBulletResistModifier', 'm_BulletResist'),
            'BulletResistReductionPerHero': json_utils.read_value(data, 'm_BackdoorBulletResistModifier', 'm_BulletResistReductionPerHero'),
        }
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_walker_aura(self, data):
        """Parses the friendly aura stats for the Walker boss."""
        stats = {
            'FriendlyAuraRadius': convert_engine_units_to_meters(json_utils.read_value(data, 'm_FriendlyAuraModifier', 'm_flAuraRadius')),
        }

        # Parse friendly aura bonuses from script values

        script_values = json_utils.deep_get(data, 'm_FriendlyAuraModifier', 'm_modifierProvidedByAura', 'm_vecScriptValues')
        if isinstance(script_values, list):
            for script_value in script_values:
                if isinstance(script_value, dict):
                    modifier_name = script_value.get('m_eModifierValue')
                    output_key = maps.get_npc_aura_modifier(modifier_name)
                    if output_key:
                        stats[output_key] = num_utils.assert_number(script_value.get('m_value'))
        return stats

    def _parse_walker_resistances(self, data):
        """Parses the various damage resistance stats for the Walker boss."""
        stats = {
            'NearbyEnemyResistanceRange': convert_engine_units_to_meters(
                json_utils.read_value(data, 'm_NearbyEnemyResist', 'm_flNearbyEnemyResistRange')
            ),
            'NearbyEnemyResistanceValues': json_utils.deep_get(data, 'm_NearbyEnemyResist', 'm_flResistValues'),
        }
        stats.update(self._parse_ranged_resistance(data))
        return stats

    def _parse_walker_backdoor_protection(self, data):
        """Parses the backdoor protection stats for the Walker boss."""
        return self._parse_backdoor_protection(data)

    def _parse_walker(self, data, npc_key=None):
        # The invulnerability range key differs between the standard and 'weak' walker variants.
        # Check for the primary key first, then fall back to the secondary.
        invuln_range_raw = json_utils.read_value(data, 'm_flInvulModifierRange')
        if invuln_range_raw is None:
            invuln_range_raw = json_utils.read_value(data, 'm_flInvulRange')

        stats = {
            'MaxHealth': json_utils.read_value(data, 'm_nMaxHealth'),
            'MeleeAttemptRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flMeleeAttemptRange')),
            'SightRangePlayers': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangePlayers')),
            'SightRangeNPCs': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangeNPCs')),
            'PlayerInitialSightRange': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flPlayerInitialSightRange')),
            'StompDamage': json_utils.read_value(data, 'm_flStompDamage'),
            'StompDamageMaxHealthPercent': json_utils.read_value(data, 'm_flStompDamageMaxHealthPercent'),
            'StompRadius': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flStompImpactRadius')),
            'StompStunDuration': json_utils.read_value(data, 'm_flStunDuration'),
            'StompKnockup': json_utils.read_value(data, 'm_flStompTossUpMagnitude'),
            'InvulnerabilityRange': convert_engine_units_to_meters(invuln_range_raw),
            'BoundAbilities': self._parse_npc_abilities(data.get('m_mapBoundAbilities')),
        }

        # Update stats by calling specialized helper methods
        stats.update(self._parse_walker_aura(data))
        stats.update(self._parse_walker_resistances(data))
        stats.update(self._parse_walker_backdoor_protection(data))
        stats.update(self._parse_intrinsic_modifiers(data))

        return stats

    def _parse_patron(self, data, npc_key=None):
        stats = {
            'MaxHealthPhase1': json_utils.read_value(data, 'm_nMaxHealth'),
            'MaxHealthPhase2': json_utils.read_value(data, 'm_nPhase2Health'),
            'SightRangePlayers': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flSightRangePlayers')),
            'MoveSpeed': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flDefaultMoveSpeed')),
            'MoveSpeedNoShield': convert_engine_units_to_meters(json_utils.read_value(data, 'm_flNoShieldMoveSpeed')),
            'LaserDPSToPlayers': json_utils.read_value(data, 'm_flLaserDPSToPlayers'),
            'LaserDPSToNPCs': json_utils.read_value(data, 'm_flLaserDPSToNPCs'),
            'LaserDPSMaxHealthPercent': json_utils.read_value(data, 'm_flLaserDPSMaxHealth'),
            'LaserDPSToPlayersNoShield': json_utils.read_value(data, 'm_flNoShieldLaserDPSToPlayers'),
            'LaserDPSToNPCsNoShield': json_utils.read_value(data, 'm_flNoShieldLaserDPSToNPCs'),
            'IsUnkillableInPhase1': 'm_Phase1Modifier' in data,
            'HealthGrowthPerMinutePhase1': json_utils.read_value(data, 'm_ObjectiveHealthGrowthPhase1', 'm_iGrowthPerMinute'),
            'HealthGrowthStartTimePhase1': json_utils.read_value(data, 'm_ObjectiveHealthGrowthPhase1', 'm_iGrowthStartTimeInMinutes'),
            'HealthGrowthPerMinutePhase2': json_utils.read_value(data, 'm_ObjectiveHealthGrowthPhase2', 'm_iGrowthPerMinute'),
            'HealthGrowthStartTimePhase2': json_utils.read_value(data, 'm_ObjectiveHealthGrowthPhase2', 'm_iGrowthStartTimeInMinutes'),
            'OutOfCombatHealthRegen': json_utils.read_value(data, 'm_ObjectiveRegen', 'm_flOutOfCombatHealthRegen'),
            'BoundAbilities': self._parse_npc_abilities(data.get('m_mapBoundAbilities')),
        }

        stats.update(self._parse_ranged_resistance(data))
        # Patron uses a slightly different key for backdoor protection
        stats.update(self._parse_backdoor_protection(data, key='m_BackdoorProtection'))
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    # --- Neutral Unit Parsers ---

    def _parse_neutral_trooper(self, data, npc_key=None):
        """Parses Neutral Troopers (weak, normal, strong)."""
        stats = {
            'MaxHealth': json_utils.read_value(data, 'm_nMaxHealth'),
            'GoldReward': json_utils.read_value(data, 'm_flGoldReward'),
            'GoldRewardBonusPercentPerMinute': json_utils.read_value(data, 'm_flGoldRewardBonusPercentPerMinute'),
        }
        stats.update(self._parse_spawn_info(npc_key))
        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_midboss(self, data, npc_key=None):
        """Parses the Midboss (npc_super_neutral)."""
        stats = {
            'StartingHealth': json_utils.read_value(data, 'm_iStartingHealth'),
            'HealthGainPerMinute': json_utils.read_value(data, 'm_iHealthGainPerMinute'),
        }

        # Parse the regenerating shield from modifiers_data
        shield_modifier = self.modifiers_data.get('midboss_modifier_damage_resistance', {})
        stats['Shield'] = {
            'BaseAbsorptionPerSecond': json_utils.read_value(shield_modifier, 'm_flDamageResistancePerSecond'),
            'ScalingAbsorptionPerMinute': json_utils.read_value(shield_modifier, 'm_flDamageResistanceBonusPerGameMinute'),
        }

        # Parse spawn times from misc_data
        stats.update(self._parse_spawn_info(npc_key))

        stats.update(self._parse_intrinsic_modifiers(data))
        return stats

    def _parse_sinners_sacrifice(self, data, npc_key=None):
        """Parses Sinner's Sacrifice (neutral_vault)."""
        stats = {
            'RetaliateDamage': json_utils.read_value(data, 'm_flRetaliateDamage'),
            'GoldReward': json_utils.read_value(data, 'm_flGoldReward'),
            'GoldRewardBonusPercentPerMinute': json_utils.read_value(data, 'm_flGoldRewardBonusPercentPerMinute'),
            'DamagedByAbilities': data.get('m_bDamagedByAbilities'),
            'DamagedByBullets': data.get('m_bDamagedByBullets'),
            'MinigameDuration': json_utils.read_value(data, 'm_flVaultMiniGameTime'),
            'MinigameHitWindow': json_utils.read_value(data, 'm_flVaultMiniGameHitWindow'),
        }
        stats.update(self._parse_spawn_info(npc_key))
        return stats

    # --- Item & Object Parsers ---

    def _parse_rejuvenator(self, data, npc_key=None):
        """Parses the Rejuvenator pickup (citadel_item_pickup_rejuv)."""
        stats = {}
        rebirth_data = data.get('m_RebirthModifier')
        if not rebirth_data:
            return stats

        stats['RespawnDelay'] = num_utils.assert_number(rebirth_data.get('m_flRespawnDelay'))
        stats['RespawnLifePercent'] = num_utils.assert_number(rebirth_data.get('m_flRespawnLifePct'))

        script_values = rebirth_data.get('m_vecScriptValues')
        if not isinstance(script_values, list):
            return stats

        for script_value in script_values:
            if not isinstance(script_value, dict):
                continue

            modifier_name = script_value.get('m_eModifierValue')
            output_key = maps.get_npc_rebirth_modifier(modifier_name)
            if output_key:
                stats[output_key] = num_utils.assert_number(script_value.get('m_value'))

        return stats
