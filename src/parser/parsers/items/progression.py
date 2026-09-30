def extract_progression(item_value):
    """Extract progression stats for provided item data (e.g. for seasonal items like Snowball)"""
    progression = {}
    for k, v in item_value.items():
        if k.startswith('m_progression'):
            prop_name = k.replace('m_progression', '')
            if isinstance(v, dict) and 'm_mapLevelsToValue' in v:
                prog_entry = {'Levels': v['m_mapLevelsToValue']}
                if 'm_eBetweenBehavior' in v:
                    prog_entry['Behavior'] = v['m_eBetweenBehavior']
                progression[prop_name] = prog_entry

    return progression
