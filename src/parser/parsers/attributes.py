import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from .constants import OUTPUT_DIR
import utils.json_utils as json_utils
import maps as maps


class AttributeParser:
    def __init__(self, heroes_data, localizations):
        self.heroes_data = heroes_data
        self.localizations = localizations

    def run(self):
        all_attributes = {}

        for hero_key, hero_value in self.heroes_data.items():
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                # Add attributes this hero contains to the master attr dict
                all_attributes.update(self._parse_stats_ui(hero_value))
                all_attributes.update(self._parse_shop_stat_display(hero_value))
        # Write to

        json_utils.write(
            OUTPUT_DIR + 'json/attribute-data.json', json_utils.sort_dict(all_attributes)
        )

    # Parse the stats that are listed in the UI in game
    def _parse_stats_ui(self, hero_value):
        """Parses m_heroStatsUI for each hero"""
        """
            Within m_heroStatsUI
            Transform each value within m_vecDisplayStats array
            
            {
                "m_eStatType": "EMaxHealth",
                "m_eStatCategory": "ECitadelStat_Vitality"
            }

            to a dict entry
            "Vitality": "MaxHealth"
        """

        category_attributes = {}

        stats_ui = hero_value['m_heroStatsUI']['m_vecDisplayStats']
        for stat in stats_ui:
            parsed_stat_name = maps.get_hero_attr(stat['m_eStatType'])
            parsed_stat_category = maps.get_attr_group(stat['m_eStatCategory'])

            # Ensure category exists
            if parsed_stat_category not in category_attributes:
                category_attributes[parsed_stat_category] = []

            # Add stat to category if not already present
            if parsed_stat_name not in category_attributes[parsed_stat_category]:
                category_attributes[parsed_stat_category].append(parsed_stat_name)

        return category_attributes

    def _parse_shop_stat_display(self, hero_value):
        """Parses m_ShopStatDisplay for each hero"""

        """
            Within m_ShopStatDisplay
            Transform
            "m_eWeaponStatsDisplay": {
                "m_vecDisplayStats": [
                    "EBulletDamage",
                ],
                "m_vecOtherDisplayStats": [
                    "ELightMeleeDamage",
                ],
                "m_eWeaponAttributes": "EWeaponAttribute_RapidFire | EWeaponAttribute_MediumRange"
            },

            to a dict entry

            "Weapon": [
                "BulletDamage",
                "LightMeleeDamage",
                "WeaponAttribute_RapidFire",
                "WeaponAttribute_MediumRange"
                ]
        """

        category_attributes = {}

        shop_stats_ui = hero_value['m_ShopStatDisplay']
        for category, category_stats in shop_stats_ui.items():
            category_name = maps.get_shop_attr_group(category)

            # Ensure category exists
            if category_name not in category_attributes:
                category_attributes[category_name] = []

            # Process all stats in the category
            for _, stats in category_stats.items():
                if type(stats) is str:
                    # Contains weapon type and weapon range
                    # May be parsed in the future, left out of this data for now
                    # stats = stats.split(' | ')
                    continue
                elif type(stats) is list:
                    pass
                else:
                    raise Exception(f'Expected string or list, got {type(stats)}')

                # Add to parsed stats
                for stat in stats:
                    stat_mapped = maps.get_hero_attr(stat)

                    # Add stat to category if not already present
                    if stat_mapped not in category_attributes[category_name]:
                        category_attributes[category_name].append(stat_mapped)

        return category_attributes
