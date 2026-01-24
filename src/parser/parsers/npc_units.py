from loguru import logger
import utils.json_utils as json_utils
import utils.num_utils as num_utils
from utils.num_utils import convert_engine_units_to_meters


class NpcParser:
    """
    Parses the npc_units.vdata file to extract stats for various NPCs.
    Uses automatic discovery for numeric, boolean, and logic flag attributes,
    handling random ranges, targeting tiers, and deep nested mechanics like stagger bars.
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
        # 'Magnitude' and 'Multiplier' are excluded as they are dimensionless scales.
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

    def _clean_valve_string(self, s, prefixes):
        """Strips Valve prefixes and converts snake_case to CamelCase."""
        temp = s
        for p in prefixes:
            temp = temp.replace(p, '')
        return ''.join(word.capitalize() for word in temp.split('_'))

    def _process_value(self, val, clean_key, prefix):
        """
        Sanitizes a value, applies unit conversion for spatial floats,
        and converts bitmask strings into logic flag lists.
        """
        # 1. Handle logic flags/bitmasks (e.g., MODIFIER_STATE_INVULNERABLE)
        if isinstance(val, str) and any(val.startswith(p) for p in ['MODIFIER_STATE_', 'MODIFIER_ATTRIBUTE_']):
            flags = val.split('|')
            return [self._clean_valve_string(f.strip(), ['MODIFIER_STATE_', 'MODIFIER_ATTRIBUTE_']) for f in flags]

        # 2. Sanitize number and handle float garbage
        sanitized_val = num_utils.assert_number(val)

        # 3. Handle unit conversion for float-prefixed spatial keywords
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

                # Handle lists (random ranges like [390, 550]) vs scalar numbers
                if isinstance(value, list):
                    results[clean_key] = [self._process_value(v, clean_key, found_prefix) for v in value]
                else:
                    results[clean_key] = self._process_value(value, clean_key, found_prefix)

        return results

    def _parse_dynamic_modifiers(self, data):
        """
        Automatically discovers resistance or buff modifiers from script values.
        Converts internal Enum strings to CamelCase and sorts the result.
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

                clean_name = self._clean_valve_string(mod_enum, ['MODIFIER_VALUE_'])
                intrinsics[clean_name] = num_utils.assert_number(script_value.get('m_value'))

        return json_utils.sort_dict(intrinsics)

    def _parse_targeting_priority(self, data):
        """Extracts AI targeting tiers (Hate Lists) into ordered clean categories."""
        raw_tiers = data.get('m_vecTargettingTiers')
        if not isinstance(raw_tiers, list):
            return None

        priority = []
        for entry in raw_tiers:
            cat = entry.get('m_eCategory', '')
            # SKELE_TARGET_HERO -> Hero
            clean_cat = cat.split('_')[-1].capitalize()
            dist = convert_engine_units_to_meters(num_utils.assert_number(entry.get('m_flRange', 0)))
            priority.append({'Category': clean_cat, 'Range': dist})

        return priority

    def run(self, strict=True):
        """Main execution logic. returns deeply alphabetized NPC data with metadata."""
        all_npcs = {}

        for key, data in self.npc_units_data.items():
            if not isinstance(data, dict) or data.get('_not_pickable'):
                continue

            npc_class = data.get('_class')
            # Route to specialized handler or fallback to generic discovery handler
            parser_method = self._get_parser_method(npc_class) or self._parse_generic_unit

            try:
                parsed_data = parser_method(data, key)
                if parsed_data:
                    # Localization fallback
                    parsed_data['Name'] = self.localizations.get(key, key)
                    # Metadata preservation for Wiki Lua modules
                    parsed_data['_class'] = npc_class
                    all_npcs[key] = json_utils.sort_dict(parsed_data)
            except Exception as e:
                logger.warning(f"Failed to parse NPC '{key}': {e}")
                if strict:
                    raise e

        return json_utils.sort_dict(all_npcs)

    def _get_parser_method(self, npc_class):
        """Routes specific engine classes to logic handlers."""
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
            'npc_necro_skele': self._parse_necro_skele,
        }
        return CLASS_MAP.get(npc_class)

    # --- Specialized Logic Handlers ---

    def _parse_generic_unit(self, data, npc_key):
        """Default categorization logic with deep sorted nested objects."""
        # 1. Root numeric/bool stats
        stats = self._crawl_stats(data)

        # 2. Weapon logic
        if 'm_WeaponInfo' in data:
            stats['Weapon'] = json_utils.sort_dict(self._crawl_stats(data['m_WeaponInfo']))

        # 3. Backdoor/Protection logic
        bd_key = 'm_BackdoorProtectionModifier' if 'm_BackdoorProtectionModifier' in data else 'm_BackdoorProtection'
        if bd_key in data:
            stats['BackdoorProtection'] = json_utils.sort_dict(self._crawl_stats(data[bd_key]))

        # 4. Resistances (Ranged Armor) logic
        if 'm_RangedArmorModifier' in data:
            stats['RangedResistance'] = json_utils.sort_dict(self._crawl_stats(data['m_RangedArmorModifier']))

        # 5. Abilities (Deep cross-reference)
        if 'm_mapBoundAbilities' in data:
            stats['BoundAbilities'] = self._parse_npc_abilities(data['m_mapBoundAbilities'])

        # 6. Modifier discovery (resistance/buffs)
        stats['Modifiers'] = self._parse_dynamic_modifiers(data)

        # 7. AI Targeting priority
        targeting = self._parse_targeting_priority(data)
        if targeting:
            stats['TargetingPriority'] = targeting

        # 8. Apply global rules
        if data.get('_class') == 'npc_trooper':
            stats['DamageReductionNearEnemyBase'] = self.trooper_damage_reduction_from_objective

        return stats

    def _parse_trooper(self, data, npc_key):
        return self._parse_generic_unit(data, npc_key)

    def _parse_neutral_unit(self, data, npc_key):
        stats = self._parse_generic_unit(data, npc_key)
        # Link to external timers in misc.vdata
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

        # Stagger Mechanics Discovery (Deep crawl)
        stagger_root = data.get('m_StaggerWatcherModifier')
        if stagger_root:
            stagger_stats = self._crawl_stats(stagger_root)
            # Dive into sub-blocks for stun/buildup stats
            for sub in ['m_StaggeredModifier', 'm_BuildUpModifier']:
                if sub in stagger_root:
                    stagger_stats.update(self._crawl_stats(stagger_root[sub]))
            stats['Stagger'] = json_utils.sort_dict(stagger_stats)

        # Discovery and nested Aura properties
        if 'm_FriendlyAuraModifier' in data:
            aura = data['m_FriendlyAuraModifier']
            aura_stats = self._crawl_stats(aura)
            inner_mod = json_utils.deep_get(aura, 'm_modifierProvidedByAura')
            if inner_mod:
                aura_stats.update(self._parse_dynamic_modifiers({'m_vecIntrinsicModifiers': [inner_mod]}))
            stats['FriendlyAura'] = json_utils.sort_dict(aura_stats)

        # Fix for falsy numeric preservation (Auditor Review): Use explicit None check
        invul_range_raw = json_utils.read_value(data, 'm_flInvulModifierRange')
        if invul_range_raw is None:
            invul_range_raw = json_utils.read_value(data, 'm_flInvulRange')
        stats['InvulnerabilityRange'] = convert_engine_units_to_meters(invul_range_raw)

        # Discovery of empowered/test level variations
        for i in range(1, 4):
            key = f'm_EmpoweredModifierLevel{i}'
            if key in data:
                stats[f'EmpoweredLevel{i}'] = json_utils.sort_dict(self._crawl_stats(data[key]))

        return stats

    def _parse_patron(self, data, npc_key):
        stats = self._parse_generic_unit(data, npc_key)
        # Discover unique growth phases
        for p in range(1, 3):
            key = f'm_ObjectiveHealthGrowthPhase{p}'
            if key in data:
                stats[f'HealthGrowthPhase{p}'] = json_utils.sort_dict(self._crawl_stats(data[key]))

        if 'm_ObjectiveRegen' in data:
            stats['OutOfCombatRegen'] = json_utils.sort_dict(self._crawl_stats(data['m_ObjectiveRegen']))

        return stats

    def _parse_midboss(self, data, npc_key):
        stats = self._parse_neutral_unit(data, npc_key)
        # Discovery of shield data from external modifiers file
        shield_modifier = self.modifiers_data.get('midboss_modifier_damage_resistance', {})
        if shield_modifier:
            stats['Shield'] = json_utils.sort_dict(self._crawl_stats(shield_modifier))
        return stats

    def _parse_rejuvenator(self, data, npc_key):
        stats = {}
        if 'm_RebirthModifier' in data:
            stats = self._crawl_stats(data['m_RebirthModifier'])
            # Crawl script values inside the modifier and sort
            stats.update(self._parse_dynamic_modifiers({'m_vecIntrinsicModifiers': [data['m_RebirthModifier']]}))
            stats = json_utils.sort_dict(stats)
        return stats

    def _parse_necro_skele(self, data, npc_key):
        return self._parse_neutral_unit(data, npc_key)

    def _parse_npc_abilities(self, raw_abilities):
        """Cross-references abilities to retrieve names and returns alphabetized result."""
        if not isinstance(raw_abilities, dict):
            return None
        formatted = {}
        for slot, ability_key in raw_abilities.items():
            num = slot.split('_')[-1] if '_' in slot else slot
            ability_data = self.parsed_abilities.get(ability_key)
            formatted[num] = {'Name': ability_data['Name'] if ability_data else ability_key, 'Key': ability_key}
        return json_utils.sort_dict(formatted)

    def _parse_spawn_info(self, npc_key):
        """Retrieves camp spawn timings from external misc data."""
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
