from parser.maps import SOUL_UNLOCK_MAP


class SoulUnlockParser:
    """
    Parses what is unlocked at certain soul thresholds

    Such as ability unlocks, points, and power increases
    """

    def __init__(self, heroes_data):
        self.heroes_data = heroes_data

    def run(self):
        parsed_soul_unlocks = {}
        hero_key_of_parsed_soul_unlocks = None

        # Parse for each hero
        for hero_key, hero_data in self.heroes_data.items():
            if 'm_mapLevelInfo' in hero_data:
                su_datas = hero_data['m_mapLevelInfo']
                hero_soul_unlocks = self._parse_hero_soul_unlocks(su_datas)

                # Initialize the result
                if parsed_soul_unlocks == {}:
                    parsed_soul_unlocks = hero_soul_unlocks
                    hero_key_of_parsed_soul_unlocks = hero_key
                # Confirm that the soul unlocks is the same as the previous hero's soul unlocks
                else:
                    if parsed_soul_unlocks != hero_soul_unlocks:
                        raise ValueError(
                            'Soul unlocks do not match between heroes'
                            + f'{hero_key_of_parsed_soul_unlocks} and {hero_key}.'
                            + ' May require a new data structure for the data '
                            + 'and [[Module:SoulUnlock]]'
                        )

        return parsed_soul_unlocks

    def _flatten_su_data(self, su_data):
        """
        Map and flatten soul unlock data to a 1 level hashmap

        Example:
        {
            m_unRequiredGold = 400
            m_bUseStandardUpgrade = true
            m_mapBonusCurrencies =
            {
                EAbilityUnlocks = 1
                EAbilityPoints = 1
            }
        }
        mapped to
        {
            RequiredSouls = 400
            PowerIncrease = true
            AbilityUnlocks = 1
            AbilityPoints = 1
        }
        Note, the mapped example is using the current content of SOUL_UNLOCK_MAP
        If the map is changed, the mapped example will not be updated.
        """

        mapped_su_data = {}
        for key, value in su_data.items():
            if key in SOUL_UNLOCK_MAP:
                mapped_su_data[SOUL_UNLOCK_MAP[key]] = value
            elif isinstance(value, dict):
                mapped_su_data.update(self._flatten_su_data(value))
            else:
                raise ValueError(
                    f'Unknown key {key} in soul unlock data. Please update SOUL_UNLOCK_MAP. '
                    + 'Map should contain all non-dict type keys'
                )

        return mapped_su_data

    def _parse_hero_soul_unlocks(self, su_datas):
        parsed_su_datas = []
        # Iterate the hashmap in order, so num (root level key) isn't needed
        for num, su_data in su_datas.items():
            flattened_su_data = self._flatten_su_data(su_data)
            parsed_su_datas.append(flattened_su_data)

        return parsed_su_datas
