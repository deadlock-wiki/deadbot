from loguru import logger

import utils.string_utils as string_utils
from parser.maps import INVESTMENT_SLOT_MAP


class ItemInvestmentParser:
    """
    Parses item investment (slot threshold) data from hero definitions.

    Every selectable hero shares the same m_MapModCostBonuses map, which
    defines the soul-cost brackets for items in each slot category (Weapon,
    Vitality, Spirit).  The parser validates consistency across all heroes
    and returns a single merged dict.
    """

    PREFIXES = ['m_str', 'm_map', 'm_n', 'm_fl', 'm_', 'fl', 'E', 'n']

    def __init__(self, heroes_data):
        self.heroes_data = heroes_data

    def _clean_keys(self, data: dict) -> dict:
        """Recursively remove prefixes from keys in a dictionary."""
        cleaned = {}
        for key, value in data.items():
            new_key = key
            for prefix in self.PREFIXES:
                new_key = string_utils.remove_prefix(key, prefix)
                if new_key != key:
                    break

            # If value is a dict, recursively clean its keys
            if isinstance(value, dict):
                value = self._clean_keys(value)

            cleaned[new_key] = value
        return cleaned

    def run(self) -> dict:
        first = None
        first_key = None

        for hero_key, hero_data in self.heroes_data.items():
            if not isinstance(hero_data, dict):
                continue
            if hero_key == 'hero_base':
                continue
            if not hero_data.get('m_bPlayerSelectable', False):
                continue
            if 'm_MapModCostBonuses' not in hero_data:
                logger.warning(f'Selectable hero {hero_key} missing m_MapModCostBonuses')
                continue

            remapped = {}
            for slot, entries in hero_data['m_MapModCostBonuses'].items():
                if slot in INVESTMENT_SLOT_MAP:
                    # Clean prefixes from keys (e.g. m_nGoldThreshold -> GoldThreshold)
                    cleaned_entries = [self._clean_keys(entry) for entry in entries]
                    remapped[INVESTMENT_SLOT_MAP[slot]] = cleaned_entries
                else:
                    logger.warning(f'Unknown investment slot {slot} in hero {hero_key}')

            if first is None:
                first = remapped
                first_key = hero_key
            else:
                if first != remapped:
                    raise ValueError(
                        f'Item investment stats differ between heroes {first_key} and {hero_key}.\n' f'{first_key}: {first}\n{hero_key}: {remapped}'
                    )

        if first is None:
            raise ValueError('Could not find m_MapModCostBonuses in any selectable hero. ' 'Item investment data cannot be extracted.')

        logger.trace(f'Extracted item investment stats from {first_key} ' '(validated across all selectable heroes)')
        return {'ItemInvestments': first}
