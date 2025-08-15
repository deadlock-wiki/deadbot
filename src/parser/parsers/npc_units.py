import math
from loguru import logger
import utils.json_utils as json_utils


class NpcParser:
    """
    Parses the npc_units.vdata file to extract stats for various NPCs,
    including troopers, bosses, neutral units, and other game objects.
    This version incorporates fixes based on an audit report.
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

        # This dispatcher maps known NPC keys to their specific parsing functions.
        # While auto-discovery of keys was considered, the data structures for
        # different NPCs are highly variable. An explicit map ensures that we
        # only parse NPCs we have explicitly written logic for, preventing
        # incorrect data from being parsed by a generic function for new,
        # unknown NPC types. This is a safer, more maintainable approach.
        self.NPC_PARSERS = {
            'trooper_normal': self._parse_trooper_ranged,
            'trooper_melee': self._parse_trooper_melee,
            'trooper_medic': self._parse_trooper_medic,
            'npc_boss_tier1': self._parse_guardian,
            'npc_barrack_boss': self._parse_base_guardian,
            'destroyable_building': self._parse_shrine,
            'npc_boss_tier2': self._parse_walker,
            'npc_boss_tier3': self._parse_patron,
            'neutral_weak': self._parse_neutral_trooper,
            'neutral_normal': self._parse_neutral_trooper,
            'neutral_strong': self._parse_neutral_trooper,
            'npc_super_neutral': self._parse_midboss,
            'neutral_vault': self._parse_sinners_sacrifice,
            'citadel_item_pickup_rejuv': self._parse_rejuvenator,
        }

    def run(self, strict=True):
        """
        The main execution method. Iterates through all known NPC keys
        and parses their data, returning a consolidated dictionary.

        Args:
            strict (bool): If True, parsing will halt and raise an exception
                           on the first error. If False, it will log the error
                           and continue with the next NPC.
        """
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

    def _deep_get(self, data, *keys, default=None):
        """Safely access nested dictionary keys."""
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return default
            data = data[key]
        return data

    def _sanitize_float(self, value, default=None):
        """Converts a value to a float, ensuring it's a finite number."""
        if value is None:
            return default
        try:
            num = float(value)
            return num if math.isfinite(num) else default
        except (ValueError, TypeError):
            return default

    # --- Trooper Parsers ---

    def _parse_trooper_shared(self, data):
        """Parses stats that are common to all trooper types."""
        stats = {
            'MaxHealth': self._sanitize_float(data.get('m_nMaxHealth')),
            'PlayerDPS': self._sanitize_float(data.get('m_flPlayerDPS')),
            'TrooperDPS': self._sanitize_float(data.get('m_flTrooperDPS')),
            'T1BossDPS': self._sanitize_float(data.get('m_flT1BossDPS')),
            'BarrackBossDPS': self._sanitize_float(data.get('m_flBarrackBossDPS')),
            'SightRangePlayers': self._sanitize_float(data.get('m_flSightRangePlayers')),
            'RunSpeed': self._sanitize_float(data.get('m_flRunSpeed')),
            'DamageReductionNearEnemyBase': self._sanitize_float(
                self._deep_get(
                    data, 'm_EnemyTrooperDamageReduction', 'm_flDamageReductionForTroopers'
                )
            ),
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
                'MeleeDamage': self._sanitize_float(data.get('m_flMeleeDamage')),
                'MeleeAttemptRange': self._sanitize_float(data.get('m_flMeleeAttemptRange')),
            }
        )
        return stats

    # --- Objective & Boss Parsers ---

    def _parse_guardian(self, data):
        return {
            'MaxHealth': self._sanitize_float(data.get('m_nMaxHealth')),
            'PlayerDPS': self._sanitize_float(data.get('m_flPlayerDPS')),
            'TrooperDPS': self._sanitize_float(data.get('m_flTrooperDPS')),
            'InvulnerabilityRange': self._sanitize_float(data.get('m_flInvulRange')),
            'PlayerDamageResistance': self._sanitize_float(data.get('m_flPlayerDamageResistPct')),
            'TrooperDamageResistanceBase': self._sanitize_float(
                data.get('m_flT1BossDPSBaseResist')
            ),
            'TrooperDamageResistanceMax': self._sanitize_float(
                data.get('m_flT1BossDPSMaxResist')
            ),
        }

    def _parse_base_guardian(self, data):
        stats = self._parse_guardian(data)
        stats.update(
            {
                'BackdoorHealthRegen': self._sanitize_float(
                    self._deep_get(
                        data, 'm_BackdoorProtectionModifier', 'm_flHealthPerSecondRegen'
                    )
                ),
                'BackdoorPlayerDamageMitigation': self._sanitize_float(
                    self._deep_get(
                        data,
                        'm_BackdoorProtectionModifier',
                        'm_flBackdoorProtectionDamageMitigationFromPlayers',
                    )
                ),
                'BackdoorBulletResistBase': self._sanitize_float(
                    self._deep_get(data, 'm_BackdoorBulletResistModifier', 'm_BulletResist')
                ),
                'BackdoorBulletResistReductionPerHero': self._sanitize_float(
                    self._deep_get(
                        data,
                        'm_BackdoorBulletResistModifier',
                        'm_BulletResistReductionPerHero',
                    )
                ),
            }
        )
        return stats

    def _parse_shrine(self, data):
        return {
            'MaxHealth': self._sanitize_float(data.get('m_iMaxHealthGenerator')),
            'AntiSnipeRange': self._sanitize_float(
                self._deep_get(data, 'm_RangedArmorModifier', 'm_flInvulnRange')
            ),
            'BulletResistBase': self._sanitize_float(
                self._deep_get(data, 'm_BackdoorBulletResistModifier', 'm_BulletResist')
            ),
            'BulletResistReductionPerHero': self._sanitize_float(
                self._deep_get(
                    data, 'm_BackdoorBulletResistModifier', 'm_BulletResistReductionPerHero'
                )
            ),
        }

    def _parse_walker(self, data):
        stats = {
            'MaxHealth': self._sanitize_float(data.get('m_nMaxHealth')),
            'StompDamage': self._sanitize_float(data.get('m_flStompDamage')),
            'StompDamageMaxHealthPercent': self._sanitize_float(
                data.get('m_flStompDamageMaxHealthPercent')
            ),
            'StompRadius': self._sanitize_float(data.get('m_flStompImpactRadius')),
            'StompStunDuration': self._sanitize_float(data.get('m_flStunDuration')),
            'StompKnockup': self._sanitize_float(data.get('m_flStompTossUpMagnitude')),
            'InvulnerabilityRange': self._sanitize_float(data.get('m_flInvulRange')),
            'FriendlyAuraSpiritArmor': self._sanitize_float(
                self._deep_get(data, 'm_FriendlyAuraModifier', 'MODIFIER_VALUE_SPIRIT_ARMOR')
            ),
            'FriendlyAuraBulletArmor': self._sanitize_float(
                self._deep_get(data, 'm_FriendlyAuraModifier', 'MODIFIER_VALUE_BULLET_ARMOR')
            ),
            'NearbyEnemyResistanceValues': self._deep_get(
                data, 'm_NearbyEnemyResist', 'm_flResistValues'
            ),
            'RangedResistanceMinRange': self._sanitize_float(
                self._deep_get(data, 'm_RangedArmorModifier', 'm_flRangeMin')
            ),
            'RangedResistanceMaxRange': self._sanitize_float(
                self._deep_get(data, 'm_RangedArmorModifier', 'm_flRangeMax')
            ),
            'BackdoorHealthRegen': self._sanitize_float(
                self._deep_get(
                    data, 'm_BackdoorProtectionModifier', 'm_flHealthPerSecondRegen'
                )
            ),
            'BackdoorPlayerDamageMitigation': self._sanitize_float(
                self._deep_get(
                    data,
                    'm_BackdoorProtectionModifier',
                    'm_flBackdoorProtectionDamageMitigationFromPlayers',
                )
            ),
        }
        return stats

    def _parse_patron(self, data):
        stats = {
            'MaxHealthPhase1': self._sanitize_float(data.get('m_nMaxHealth')),
            'MaxHealthPhase2': self._sanitize_float(data.get('m_nPhase2Health')),
            'LaserDPSToPlayers': self._sanitize_float(data.get('m_flLaserDPSToPlayers')),
            'LaserDPSMaxHealthPercent': self._sanitize_float(
                data.get('m_flLaserDPSMaxHealth')
            ),
            'IsUnkillableInPhase1': 'm_Phase1Modifier' in data,
            'HealthGrowthPerMinute': self._sanitize_float(
                self._deep_get(
                    data, 'm_ObjectiveHealthGrowthPhase1', 'm_iGrowthPerMinute'
                )
            ),
            'RangedResistanceMinRange': self._sanitize_float(
                self._deep_get(data, 'm_RangedArmorModifier', 'm_flRangeMin')
            ),
            'RangedResistanceMaxRange': self._sanitize_float(
                self._deep_get(data, 'm_RangedArmorModifier', 'm_flRangeMax')
            ),
            'BackdoorHealthRegen': self._sanitize_float(
                self._deep_get(data, 'm_BackdoorProtection', 'm_flHealthPerSecondRegen')
            ),
            'BackdoorPlayerDamageMitigation': self._sanitize_float(
                self._deep_get(
                    data,
                    'm_BackdoorProtection',
                    'm_flBackdoorProtectionDamageMitigationFromPlayers',
                )
            ),
        }
        return stats

    # --- Neutral Unit Parsers ---

    def _parse_neutral_trooper(self, data):
        """Parses Neutral Troopers (weak, normal, strong)."""
        stats = {
            'MaxHealth': self._sanitize_float(data.get('m_nMaxHealth')),
            'PlayerDPS': self._sanitize_float(data.get('m_flPlayerDPS')),
            'GoldReward': self._sanitize_float(data.get('m_flGoldReward')),
            'GoldRewardBonusPercentPerMinute': self._sanitize_float(
                data.get('m_flGoldRewardBonusPercentPerMinute')
            ),
        }
        # Intrinsic modifiers are stored in a list of dictionaries.
        if 'm_vecIntrinsicModifiers' in data:
            for modifier in data['m_vecIntrinsicModifiers']:
                if (
                    modifier.get('m_strModifierName')
                    == 'MODIFIER_VALUE_BULLET_DAMAGE_REDUCTION_PERCENT'
                ):
                    stats['IntrinsicBulletResistance'] = modifier.get('m_flValue')
                elif (
                    modifier.get('m_strModifierName')
                    == 'MODIFIER_VALUE_ABILITY_DAMAGE_REDUCTION_PERCENT'
                ):
                    stats['IntrinsicAbilityResistance'] = modifier.get('m_flValue')
        return stats

    def _parse_midboss(self, data):
        """Parses the Midboss (npc_super_neutral)."""
        stats = {
            'StartingHealth': self._sanitize_float(data.get('m_iStartingHealth')),
            'HealthGainPerMinute': self._sanitize_float(data.get('m_iHealthGainPerMinute')),
            'PlayerDPS': self._sanitize_float(data.get('m_flPlayerDPS')),
        }
        if 'm_vecIntrinsicModifiers' in data:
            for modifier in data['m_vecIntrinsicModifiers']:
                if (
                    modifier.get('m_strModifierName')
                    == 'MODIFIER_VALUE_HEALTH_REGEN_PER_SECOND'
                ):
                    stats['HealthRegenPerSecond'] = modifier.get('m_flValue')
        return stats

    def _parse_sinners_sacrifice(self, data):
        """Parses Sinner's Sacrifice (neutral_vault)."""
        return {
            'RetaliateDamage': self._sanitize_float(data.get('m_flRetaliateDamage')),
            'GoldReward': self._sanitize_float(data.get('m_flGoldReward')),
            'GoldRewardBonusPercentPerMinute': self._sanitize_float(
                data.get('m_flGoldRewardBonusPercentPerMinute')
            ),
        }

    # --- Item & Object Parsers ---

    def _parse_rejuvenator(self, data):
        """Parses the Rejuvenator pickup (citadel_item_pickup_rejuv)."""
        stats = {}
        if 'm_RebirthModifier' in data:
            rebirth_data = data['m_RebirthModifier']
            stats['RespawnDelay'] = rebirth_data.get('m_flRespawnDelay')
            # The bonuses are in a list of floats.
            # Based on the request, we can assign them by their index.
            if 'm_vecScriptValues' in rebirth_data and len(
                rebirth_data['m_vecScriptValues']
            ) >= 3:
                script_values = rebirth_data['m_vecScriptValues']
                stats['BonusMaxHealth'] = script_values[0]
                stats['BonusFireRate'] = script_values[1]
                stats['BonusSpiritDamage'] = script_values[2]
        return stats
