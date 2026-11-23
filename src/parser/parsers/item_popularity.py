"""Parse the per-hero Popular Items pick/win rates from heroes.vdata."""

PHASES = {
    'ECitadelItemGamePhase_EarlyGame': 'early',
    'ECitadelItemGamePhase_MidGame': 'mid',
    'ECitadelItemGamePhase_LateGame': 'late',
}


class ItemPopularityParser:
    def __init__(self, heroes_data):
        self.heroes_data = heroes_data

    def run(self):
        result = {}
        for hero_key, hero in self.heroes_data.items():
            if not isinstance(hero, dict):
                continue
            popular = hero.get('m_PopularItems')
            if not isinstance(popular, dict):
                continue

            phases = {}
            generated = popular.get('m_mapGeneratedItemPopularity') or {}
            for raw_phase, phase_name in PHASES.items():
                items = generated.get(raw_phase) or {}
                phase = {}
                for item_key, stats in items.items():
                    if not isinstance(stats, dict):
                        continue
                    pick = stats.get('m_flPickPct')
                    win = stats.get('m_flWinratePct')
                    if pick is None or win is None:
                        continue
                    phase[item_key] = [round(pick, 2), round(win, 2)]
                if phase:
                    phases[phase_name] = phase

            if phases:
                result[hero_key] = {
                    'timestamp': popular.get('m_unTimestamp'),
                    'phases': phases,
                }
        return result
