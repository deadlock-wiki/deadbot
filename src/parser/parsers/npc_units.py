from loguru import logger
import utils.json_utils as json_utils
import utils.num_utils as num_utils
from utils.num_utils import convert_engine_units_to_meters


class NpcParser:
    """
    Parses the npc_units.vdata file to extract stats for various NPCs.
    Uses automatic discovery to crawl numeric and boolean attributes, handling
    random ranges (lists), preventing greedy prefix stripping, and providing
    deep alphabetized sorting of the entire output.
    """

    def __init__(self, npc_units_data, modifiers_data, misc_data, localizations, parsed_abilities):
        """
        Initializes the parser with necessary data and configuration.
        """
        self.npc_units_data = npc_units_data
        self.modifiers_data = modifiers_data
        self.misc_data = misc_data
        self.localizations = localizations
        self.parsed_abilities = parsed_abilities

        # Prefix list for automatic discovery based on Valve's Hungarian notation.
        self.STAT_PREFIXES = ['m_fl', 'm_n', 'm_i', 'm_b']

        # Keywords in float keys that trigger Inch -> Meter conversion.
        self.UNIT_CONVERSION_KEYWORDS = ['Range', 'Speed', 'Radius', 'Distance', 'Height', 'Width', 'Offset']

        # Scan for global game rules (e.g. Trooper damage reduction near enemy base).
        self.trooper_damage_reduction_from_objective = self._find_global_stat('m_EnemyTrooperDamageReduction', 'm_flDamageReductionForTroopers')

    def _find_global_stat(self, *keys):
        """Searches across all NPC entries to find a specific nested rule property."""
        for unit_data in self.npc_units_data.values():
            if not isinstance(unit_data, dict):
                continue
            val = json_utils.read_value(unit_data, *keys)
            if val is not None:
                return val
        return None

    def _process_value(self, val, clean_key, prefix):
        """
        Sanitizes a single numeric/bool value and applies unit conversion if required.
        """
        sanitized_val = num_utils.assert_number(val)

        # Apply spatial conversion only to float prefixes (m_fl) with spatial keywords.
        if prefix == 'm_fl' and any(word in clean_key for word in self.UNIT_CONVERSION_KEYWORDS):
            return convert_engine_units_to_meters(sanitized_val)

        return sanitized_val

    def _crawl_stats(self, data_dict):
        """
        Automatically extracts numeric and boolean attributes based on prefix.
        Handles scalars, lists (random ranges), and enforces capitalization boundaries.
        """
        results = {}
        if not isinstance(data_dict, dict):
            return results

        for key, value in data_dict.items():
            found_prefix = None
            for prefix in self.STAT_PREFIXES:
                # Prefix check: must start with prefix AND next character must be Uppercase
                # This prevents mangling metadata like 'm_navHull' (navigation)
                if key.startswith(prefix) and len(key) > len(prefix) and key[len(prefix)].isupper():
                    found_prefix = prefix
                    break

            if found_prefix:
                clean_key = key[len(found_prefix) :]

                # Handle lists (ranges like [min, max]) vs scalar numbers
                if isinstance(value, list):
                    results[clean_key] = [self._process_value(v, clean_key, found_prefix) for v in value]
                else:
                    results[clean_key] = self._process_value(value, clean_key, found_prefix)

        return results

    def _parse_dynamic_modifiers(self, data):
        """
        Automatically discovers resistance or buff modifiers from script values.
        Converts Enums (MODIFIER_VALUE_BULLET_RESIST) to CamelCase (BulletResist) and sorts.
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
                mod_enum = script_value.get('m_eModifierValue')
                if not mod_enum:
                    continue

                # Strip Enum prefix and convert to CamelCase
                raw_name = mod_enum.replace('MODIFIER_VALUE_', '')
                clean_name = ''.join(word.capitalize() for word in raw_name.split('_'))

                intrinsics[clean_name] = num_utils.assert_number(script_value.get('m_value'))

        return json_utils.sort_dict(intrinsics)

    def run(self, strict=True):
        """Main execution logic. Returns an alphabetized collection of parsed NPCs."""
        all_npcs = {}

        for key, data in self.npc_units_data.items():
            if not isinstance(data, dict) or data.get('_not_pickable'):
                continue

            npc_class = data.get('_class')
            # specialized handler or generic unit fallback
            parser_method = self._get_parser_method(npc_class) or self._parse_generic_unit

            try:
                parsed_data = parser_method(data, key)
                if parsed_data:
                    parsed_data['Name'] = self.localizations.get(key, key)
                    # The handlers ensure nested blocks are sorted
                    all_npcs[key] = json_utils.sort_dict(parsed_data)
            except Exception as e:
                logger.warning(f"Failed to parse NPC '{key}': {e}")
                if strict:
                    raise e

        # Final sort on top-level NPC keys
        return json_utils.sort_dict(all_npcs)

    def _get_parser_method(self, npc_class):
        """Routes specific engine classes to specialized logic handlers."""
        CLASS_MAP = {
            'npc_trooper': self._parse_trooper,
            'npc_trooper_boss': self._parse_guardian,
            'npc_barrack_boss': self._parse_base_guardian,
            'destroyable_building': self._parse_shrine,
            'npc_boss_tier2': self._parse_walker,
            'npc_boss_tier3': self._parse_patron,
            'npc_trooper_neutral': self._parse_neutral_unit,
            'npc_super_neutral': self._parse_midboss,
            'npc_neutral_sinners_sacrifice': self._parse_neutral_unit,
            'npc_neutral_sinners_sacrifice_hideout': self._parse_neutral_unit,
            'citadel_item_pickup_rejuv': self._parse_rejuvenator,
            'citadel_item_pickup_rejuv_herotest': self._parse_rejuvenator,
        }
        return CLASS_MAP.get(npc_class)

    def _is_class(self, data, target_class):
        """Internal class string verification."""
        return data.get('_class') == target_class

    # --- Categorization Logic ---

    def _parse_generic_unit(self, data, npc_key):
        """Default categorization handler with deep sorted nested objects."""
        # 1. Root Stats
        stats = self._crawl_stats(data)

        # 2. Weapon (Sorted)
        if 'm_WeaponInfo' in data:
            stats['Weapon'] = json_utils.sort_dict(self._crawl_stats(data['m_WeaponInfo']))

        # 3. Backdoor/Protection (Sorted)
        bd_key = 'm_BackdoorProtectionModifier' if 'm_BackdoorProtectionModifier' in data else 'm_BackdoorProtection'
        if bd_key in data:
            stats['BackdoorProtection'] = json_utils.sort_dict(self._crawl_stats(data[bd_key]))

        # 4. Resistances (Sorted)
        if 'm_RangedArmorModifier' in data:
            stats['RangedResistance'] = json_utils.sort_dict(self._crawl_stats(data['m_RangedArmorModifier']))

        # 5. Modifiers (Self-sorted)
        stats['Modifiers'] = self._parse_dynamic_modifiers(data)

        # 6. Abilities (Self-sorted)
        if 'm_mapBoundAbilities' in data:
            stats['BoundAbilities'] = self._parse_npc_abilities(data['m_mapBoundAbilities'])

        # 7. Global Rules
        if self._is_class(data, 'npc_trooper'):
            stats['DamageReductionNearEnemyBase'] = self.trooper_damage_reduction_from_objective

        return stats

    def _parse_trooper(self, data, npc_key):
        return self._parse_generic_unit(data, npc_key)

    def _parse_neutral_unit(self, data, npc_key):
        stats = self._parse_generic_unit(data, npc_key)
        # Merges external timers from misc.vdata
        stats.update(self._parse_spawn_info(npc_key))
        return stats

    def _parse_guardian(self, data, npc_key):
        return self._parse_generic_unit(data, npc_key)

    def _parse_base_guardian(self, data, npc_key):
        stats = self._parse_generic_unit(data, npc_key)
        if 'm_BackdoorBulletResistModifier' in data:
            stats['BackdoorBulletResist'] = json_utils.sort_dict(self._crawl_stats(data['m_BackdoorBulletResistModifier']))
        return stats

    def _parse_shrine(self, data, npc_key):
        return self._parse_base_guardian(data, npc_key)

    def _parse_walker(self, data, npc_key):
        stats = self._parse_generic_unit(data, npc_key)

        if 'm_FriendlyAuraModifier' in data:
            aura = data['m_FriendlyAuraModifier']
            aura_stats = self._crawl_stats(aura)
            inner_mod = json_utils.deep_get(aura, 'm_modifierProvidedByAura')
            if inner_mod:
                aura_stats.update(self._parse_dynamic_modifiers({'m_vecIntrinsicModifiers': [inner_mod]}))
            stats['FriendlyAura'] = json_utils.sort_dict(aura_stats)

        invul_range_raw = json_utils.read_value(data, 'm_flInvulModifierRange')
        if invul_range_raw is None:
            invul_range_raw = json_utils.read_value(data, 'm_flInvulRange')
        stats['InvulnerabilityRange'] = convert_engine_units_to_meters(invul_range_raw)

        for i in range(1, 4):
            key = f'm_EmpoweredModifierLevel{i}'
            if key in data:
                stats[f'EmpoweredLevel{i}'] = json_utils.sort_dict(self._crawl_stats(data[key]))

        return stats

    def _parse_patron(self, data, npc_key):
        stats = self._parse_generic_unit(data, npc_key)
        for p in range(1, 3):
            key = f'm_ObjectiveHealthGrowthPhase{p}'
            if key in data:
                stats[f'HealthGrowthPhase{p}'] = json_utils.sort_dict(self._crawl_stats(data[key]))

        if 'm_ObjectiveRegen' in data:
            stats['OutOfCombatRegen'] = json_utils.sort_dict(self._crawl_stats(data['m_ObjectiveRegen']))

        return stats

    def _parse_midboss(self, data, npc_key):
        stats = self._parse_neutral_unit(data, npc_key)
        shield_modifier = self.modifiers_data.get('midboss_modifier_damage_resistance', {})
        if shield_modifier:
            stats['Shield'] = json_utils.sort_dict(self._crawl_stats(shield_modifier))
        return stats

    def _parse_rejuvenator(self, data, npc_key):
        stats = {}
        if 'm_RebirthModifier' in data:
            stats = self._crawl_stats(data['m_RebirthModifier'])
            stats.update(self._parse_dynamic_modifiers({'m_vecIntrinsicModifiers': [data['m_RebirthModifier']]}))
            stats = json_utils.sort_dict(stats)
        return stats

    def _parse_npc_abilities(self, raw_abilities):
        """Cross-references abilities and returns alphabetized result."""
        if not isinstance(raw_abilities, dict):
            return None
        formatted = {}
        for slot, ability_key in raw_abilities.items():
            num = slot.split('_')[-1] if '_' in slot else slot
            ability_data = self.parsed_abilities.get(ability_key)
            formatted[num] = {'Name': ability_data['Name'] if ability_data else ability_key, 'Key': ability_key}
        return json_utils.sort_dict(formatted)

    def _parse_spawn_info(self, npc_key):
        """Retrieves camp timings and returns an alphabetized dict."""
        SPAWNER_MAP = {
            'neutral_trooper_weak': 'neutral_camp_weak',
            'neutral_trooper_normal': 'neutral_camp_medium',
            'neutral_trooper_strong': 'neutral_camp_strong',
            'npc_super_neutral': 'neutral_camp_midboss',
            'neutral_sinners_sacrifice': 'neutral_camp_vaults',
        }
        spawner_key = SPAWNER_MAP.get(npc_key)
        if spawner_key and spawner_key in self.misc_data:
            return json_utils.sort_dict(self._crawl_stats(self.misc_data[spawner_key]))
        return {}
