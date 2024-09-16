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

        # Extract the attributes names and group them by what category they belong to
        for hero_key, hero_value in self.heroes_data.items():
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                # Add attributes this hero contains to the master attr dict
                all_attributes.update(self._parse_stats_ui(hero_value))
                all_attributes.update(self._parse_shop_stat_display(hero_value))

        # Determine the unlocalized name of each attribute that they should map to
        all_attributes.update(self._map_to_unlocalized(all_attributes))

        # Reorder 1st level to be in the following order
        category_order = ['Weapon', 'Vitality', 'Spirit']
        all_attributes = {
            category: all_attributes[category]
            for category in category_order
            if category in all_attributes
        }

        # Write the attributes to a json file
        json_utils.write(OUTPUT_DIR + 'json/attribute-data.json', all_attributes)

    def _map_to_unlocalized(self, all_attributes):
        """Maps the attributes to their unlocalized names"""
        """
        Maps attributes as they appear in shop UI data, such as "BulletDamage" to their unlocalized names "StatDesc_BulletDamage"
        The unlocalized name will then be localized on the front end
        """

        manual_map = maps.get_attr_manual_map()

        for category, attributes in all_attributes.items():
            for attribute in attributes.keys():
                # Check if any of the following affix_patterns exist in localization
                # Affix stands for {prefix, label, postfix} - better name pending
                affix_patterns = {
                    'label': [attribute, 'StatDesc_' + attribute, attribute + '_label'],
                    'postfix': ['StatDesc_' + attribute + '_postfix', attribute + '_postfix'],
                }
                for affix_type, patterns in affix_patterns.items():
                    for pattern in patterns:
                        if pattern in self.localizations:
                            all_attributes[category][attribute][affix_type] = pattern
                            break

                # Manually map the remaining attributes
                if attribute in manual_map:
                    for affix_type in affix_patterns.keys():
                        if affix_type in manual_map[attribute]:
                            manual_map_entry = manual_map[attribute][affix_type]
                            all_attributes[category][attribute][affix_type] = manual_map_entry

                else:
                    # Ensure the label is set for all attributes; though the postfix can be blank
                    if 'label' not in all_attributes[category][attribute]:
                        raise Exception(
                            f'Unlocalized name not found for {attribute}, find the label and postfix in localization data and add them to the manual_map'
                        )

                # Add the alternate name which currently is whats used in the hero data, therefore used to link to hero data
                # Refraining from labeling this something like "hero_stat_name" as it's likely not restricted to hero
                all_attributes[category][attribute]['alternate_name'] = unlocalized_to_base_name(
                    all_attributes[category][attribute]['label']
                )

        return all_attributes

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
                category_attributes[parsed_stat_category] = {}

            # Add stat to category if not already present
            if parsed_stat_name not in category_attributes[parsed_stat_category]:
                category_attributes[parsed_stat_category][parsed_stat_name] = {}

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
                category_attributes[category_name] = {}

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
                        category_attributes[category_name][stat_mapped] = {}

        return category_attributes


def unlocalized_to_base_name(unlocalized_name):
    """Returns the base name of an unlocalized name"""
    # i.e. StatDesc_Vitality_label -> Vitality
    # base name represents the name that is either used in the shop UI, or the hero data
    if unlocalized_name.startswith('StatDesc_'):
        unlocalized_name = unlocalized_name.split('StatDesc_')[1]
    return unlocalized_name.split('_label')[0].split('_postfix')[0]
