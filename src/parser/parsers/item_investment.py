from loguru import logger

from parser.maps import INVESTMENT_SLOT_MAP


class ItemInvestmentParser:
    """
    Parses item investment (slot threshold) data from hero definitions.

    Every selectable hero shares the same m_MapModCostBonuses map, which
    defines the soul-cost brackets for items in each slot category (Weapon,
    Vitality, Spirit).  The parser validates consistency across all heroes
    and returns a single merged dict.
    """

    def __init__(self, heroes_data):
        self.heroes_data = heroes_data

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
                    remapped[INVESTMENT_SLOT_MAP[slot]] = entries
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
