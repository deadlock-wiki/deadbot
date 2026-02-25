from loguru import logger
import utils.json_utils as json_utils
import utils.num_utils as num_utils
from utils.num_utils import convert_engine_units_to_meters
from . import weapon_parser


class NpcParser:
    """
    Parses npc_units.vdata generically.
    It recursively crawls the data, strips Hungarian notation (prefixes),
    converts units to meters where appropriate, and flattens modifier lists.
    Filters out audiovisual data (particles, sounds, models) to focus on gameplay stats.
    """

    def __init__(self, npc_units_data, modifiers_data, misc_data, localizations, abilities_data):
        self.npc_units_data = npc_units_data
        self.modifiers_data = modifiers_data
        self.misc_data = misc_data
        self.localizations = localizations
        self.abilities_data = abilities_data

        # Define prefixes
        # m_nav is added to prevent m_n from matching m_navHull -> avHull
        raw_prefixes = ['m_fl', 'm_b', 'm_n', 'm_i', 'm_str', 'm_vec', 'm_map', 'm_e', 'm_subclass', 'm_s', 'm_', 'm_nav', 'MODIFIER_VALUE_']

        # Sort by length descending to ensure "m_nav" (len 5) is matched before "m_n" (len 3)
        self.PREFIXES = sorted(raw_prefixes, key=len, reverse=True)

        # Substrings in keys that indicate the value is a distance/velocity and should be converted to meters
        self.DISTANCE_KEYWORDS = ['Range', 'Radius', 'Distance', 'Speed', 'Height', 'Width', 'Velocity']

        # Substrings to exclude from unit conversion (e.g. "SpeedPercent" is a %, not a distance)
        self.DISTANCE_EXCLUDE_KEYWORDS = ['Percent', 'Pct', 'Time', 'Duration', 'Delay', 'Rate', 'Scale', 'Angle']

        # Keys containing these substrings will be completely ignored
        # This filters out audiovisual / cosmetic data
        self.KEY_BLOCKLIST = [
            'Particle',
            'Sound',
            'Decal',
            'Material',
            'Model',
            'Icon',
            'Anim',
            'Widget',
            'Config',
            'Class',
            'Attachment',
            'Effect',
            'Hint',
            'Whiz',
            'Glow',
            'HealthBar',
            'Hud',
            'Display',
            'Localization',
            'NearDeathModifier',
            '_multibase',
            '_editor',
            'itsPostCastEnabledStateMask',
            'itsChannelEnabledStateMask',
            'itsPreCastEnabledStateMask',
        ]

        # Exceptions to the blocklist (stats that might contain blocked words)
        # e.g. "Effectiveness" contains "Effect"
        self.KEY_ALLOWLIST = ['Effectiveness', 'AffectedBy', 'HitWindow']

    def run(self, strict=False):
        all_npcs = {}

        # Iterate over every entry in the npc_units file
        for key, data in self.npc_units_data.items():
            # Skip base classes or metadata if they don't look like actual units
            if key.startswith('base_') or key == 'generic_data_type':
                continue

            try:
                # 1. localized name
                unit_name = self.localizations.get(key, key)

                # 2. Generic recursive parse of the raw data
                parsed_data = self._recursive_parse(data)

                # 3. Add metadata
                # parsed_data might be None if everything was filtered out (unlikely for a unit)
                if not isinstance(parsed_data, dict):
                    parsed_data = {}

                parsed_data['Name'] = unit_name

                # 4. Enhance with external data (Spawn times, Shields from modifiers file)
                self._enhance_with_external_data(key, parsed_data)

                # 5. Parse BoundAbilities using generic parser to capture all nested data
                if 'BoundAbilities' in parsed_data:
                    parsed_data['BoundAbilities'] = self._parse_npc_abilities(parsed_data['BoundAbilities'])

                all_npcs[key] = json_utils.sort_dict(parsed_data)

            except Exception as e:
                logger.error(f"Failed to parse NPC '{key}': {e}")
                if strict:
                    raise e

        return all_npcs

    def _recursive_parse(self, data):
        """
        Recursively walks the data structure.
        Returns: The parsed value, or None if the value should be discarded.
        """
        if isinstance(data, dict):
            parsed = {}

            # Extract value from standard stat objects to allow unit conversion
            if 'm_strValue' in data:
                raw_value = data.get('m_strValue')
                return num_utils.assert_number(raw_value)

            # 1. Special Handling: Flatten Intrinsic Modifiers / Script Values
            # We merge these into the 'parsed' dict instead of returning early
            if 'm_vecScriptValues' in data and isinstance(data['m_vecScriptValues'], list):
                parsed.update(self._flatten_script_values(data['m_vecScriptValues']))

            # 2. Parse Sibling Keys
            for key, value in data.items():
                # Skip the script values (already handled) and internal identifiers
                if key == 'm_vecScriptValues' or key in ['_class', '_my_subclass_name', '_base', '_not_pickable']:
                    continue

                clean_key = self._clean_key_name(key)

                # Check Blocklist
                if self._is_blocked(clean_key):
                    continue

                # Special handling for WeaponInfo - parse using shared weapon parser
                if clean_key == 'WeaponInfo' and isinstance(value, dict):
                    parsed[clean_key] = weapon_parser.parse_weapon_info(value)
                    continue

                parsed_val = self._recursive_parse(value)

                # Post-process value (Unit conversion)
                parsed_val = self._post_process_value(clean_key, parsed_val)

                # Add to result if it's a valid value
                # We filter out None, and empty dictionaries/lists (pruning)
                if self._is_valid_value(parsed_val):
                    parsed[clean_key] = parsed_val

            # If dict is empty after filtering, return None to prune it from parent
            return parsed if parsed else None

        elif isinstance(data, list):
            # Recurse items
            parsed_list = []
            for item in data:
                val = self._recursive_parse(item)
                if self._is_valid_value(val):
                    parsed_list.append(val)
            return parsed_list if parsed_list else None

        elif isinstance(data, str):
            # Strict String Filtering for Assets/Sounds

            # 1. Filter out file paths (Particles, Models, Icons)
            if '/' in data or '\\' in data or '.vpcf' in data or '.vmdl' in data or '.vsnd' in data or '.png' in data:
                return None

            # 2. Filter out Sound Events (Dot notation, no spaces)
            # e.g. "Guardian.Tier1.Activate", "Base.Bullet.Whizby"
            # We ensure it's not a floating point number string (which might have a dot)
            if '.' in data and ' ' not in data:
                try:
                    float(data)
                except ValueError:
                    # It has a dot, no spaces, and isn't a number. It's likely a sound event.
                    return None

            return data

        else:
            # Base value (int, float, bool)
            return num_utils.assert_number(data)

    def _is_blocked(self, key):
        """Returns True if the key should be ignored based on the blocklist."""
        # Check allowlist first
        for allowed in self.KEY_ALLOWLIST:
            if allowed in key:
                return False

        # Check blocklist
        for blocked in self.KEY_BLOCKLIST:
            if blocked in key:
                return True
        return False

    def _is_valid_value(self, value):
        """
        Determines if a value should be kept.
        Keeps: False, 0, non-empty structures.
        Discards: None, {}, [].
        """
        if value is None:
            return False
        if isinstance(value, (dict, list)) and len(value) == 0:
            return False
        return True

    def _clean_key_name(self, key):
        """Removes Hungarian notation prefixes."""
        for prefix in self.PREFIXES:
            if key.startswith(prefix):
                # Ensure we don't strip the whole key if it is just the prefix (unlikely)
                if len(key) > len(prefix):
                    return key[len(prefix) :]
        return key

    def _post_process_value(self, key, value):
        """
        Converts engine units to meters if the key suggests it's a distance.
        """
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if any(k in key for k in self.DISTANCE_KEYWORDS) and not any(ex in key for ex in self.DISTANCE_EXCLUDE_KEYWORDS):
                return convert_engine_units_to_meters(value)
        return value

    def _flatten_script_values(self, script_values_list):
        """
        Flattens Valve's modifier script value list into a simple dictionary.
        """
        flat = {}
        for item in script_values_list:
            if not isinstance(item, dict):
                continue

            modifier_enum = item.get('m_eModifierValue')
            val = num_utils.assert_number(item.get('m_value'))

            if modifier_enum:
                if modifier_enum.startswith('MODIFIER_VALUE_'):
                    modifier_enum = modifier_enum[len('MODIFIER_VALUE_') :]
                flat[modifier_enum] = val
        return flat

    def _parse_npc_abilities(self, bound_abilities):
        """
        Parse NPC abilities using generic recursive parsing.
        This captures all custom nested data structures (weapons, modifiers, etc.).
        """
        if not isinstance(bound_abilities, dict):
            return bound_abilities

        resolved = {}
        for slot, ability_key in bound_abilities.items():
            # Get raw ability data
            raw_ability = self.abilities_data.get(ability_key)

            if not raw_ability:
                # Fallback for missing abilities
                resolved[slot] = {
                    'Key': ability_key,
                    'Name': self.localizations.get(ability_key, ability_key),
                }
                continue

            # Use generic recursive parsing to capture everything
            parsed_ability = self._recursive_parse(raw_ability)

            if not isinstance(parsed_ability, dict):
                parsed_ability = {}

            # Ensure key metadata is present
            parsed_ability['Key'] = ability_key
            parsed_ability['Name'] = self.localizations.get(ability_key, ability_key)

            resolved[slot] = parsed_ability

        return resolved

    def _enhance_with_external_data(self, npc_key, parsed_data):
        """
        Injects data from misc.vdata (spawn times) or modifiers (shields).
        """
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
            if 'm_iInitialSpawnDelayInSeconds' in spawner_data:
                parsed_data['InitialSpawnDelay'] = spawner_data['m_iInitialSpawnDelayInSeconds']
            if 'm_iSpawnIntervalInSeconds' in spawner_data:
                parsed_data['SpawnInterval'] = spawner_data['m_iSpawnIntervalInSeconds']

        # Midboss Shield (from modifiers.vdata)
        if npc_key == 'npc_super_neutral':
            shield_modifier = self.modifiers_data.get('midboss_modifier_damage_resistance')
            if shield_modifier:
                parsed_data['ShieldLogic'] = {
                    'BaseAbsorptionPerSecond': json_utils.read_value(shield_modifier, 'm_flDamageResistancePerSecond'),
                    'ScalingAbsorptionPerMinute': json_utils.read_value(shield_modifier, 'm_flDamageResistanceBonusPerGameMinute'),
                }

        # Trooper Enemy Base Resistance (from modifiers.vdata)
        if npc_key in ['trooper_base', 'trooper_normal', 'trooper_medic', 'trooper_melee', 'trooper_necro']:
            resist_modifier = self.modifiers_data.get('modifier_citadel_trooper_in_enemy_base_resist')
            if resist_modifier:
                parsed_data['EnemyBaseDamageReduction'] = resist_modifier.get('m_flDamageReductionForTroopers')
