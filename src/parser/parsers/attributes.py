import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from .constants import OUTPUT_DIR
import utils.json_utils as json_utils
import maps as maps


class AttributeParser:
    """
    Output-data is used by https://deadlocked.wiki/Template:Infobox_stat 
    and /Module:HeroData
    to display a hero's attributes on their hero page
    """

    def __init__(self, heroes_data, localizations):
        self.heroes_data = heroes_data
        self.localizations = localizations

    def run(self):
        all_attributes = {}

        # Extract the attributes names and group them by what category they belong to
        for hero_key, hero_value in self.heroes_data.items():
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                shop_stats_ui = hero_value['m_ShopStatDisplay']
                for category, category_stats in shop_stats_ui.items():
                    # Ensure category exists
                    category_name = maps.get_shop_attr_group(category)
                    if category_name not in all_attributes:
                        all_attributes[category_name] = {}

                    # Add attributes this hero contains to the categories' stats
                    all_attributes[category_name].update(
                        self._parse_shop_stat_display(category_stats)
                    )

        # Specify order for lua as it isn't capable of iterating jsons in the order it appears
        order_lists = {}
        category_order = ['Weapon', 'Vitality', 'Spirit']
        for category, attributes in all_attributes.items():
            # Convert to list of the stats in order
            attributes_order = list(attributes.keys())
            order_lists[category] = {}
            order_lists[category]['attribute_order'] = attributes_order
        order_lists['category_order'] = category_order
        json_utils.write(OUTPUT_DIR + '/json/stat-infobox-order.json', order_lists)

        # Manually add DPS to the Weapon category
        all_attributes['Weapon']['DPS'] = {}

        # Determine the unlocalized name of each attribute that they should map to
        all_attributes.update(self._map_to_unlocalized(all_attributes))

        # Reorder 1st level to be in the order they are displayed in game
        # and which happens to be the best for UX reasons
        all_attributes = {
            category: all_attributes[category]
            for category in category_order
            if category in all_attributes
        }

        # Write the attributes to a json file
        json_utils.write(OUTPUT_DIR+'/json/attribute-data.json', all_attributes)

    def _map_to_unlocalized(self, all_attributes):
        """
        Maps the attributes to their unlocalized names,
        Maps the attributes to their unlocalized names,
        such as "BulletDamage" to their unlocalized names "StatDesc_BulletDamage"
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
                            f'Unlocalized name not found for {attribute}, '
                            + 'find the label and postfix'
                            + ' in localization data and add them to the manual_map'
                        )

        return all_attributes

    def _parse_shop_stat_display(self, category_stats):
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
                ]
        """

        category_attributes = {}

        # Process all stats in the category
        stats = []
        if 'm_vecDisplayStats' in category_stats:
            stats += category_stats['m_vecDisplayStats']
        if 'm_vecOtherDisplayStats' in category_stats:
            stats += category_stats['m_vecOtherDisplayStats']
        # Process all stats in the category
        stats = []
        if 'm_vecDisplayStats' in category_stats:
            stats += category_stats['m_vecDisplayStats']
        if 'm_vecOtherDisplayStats' in category_stats:
            stats += category_stats['m_vecOtherDisplayStats']

        # Add to parsed stats
        for stat in stats:
            stat_mapped = maps.get_hero_attr(stat)
        # Add to parsed stats
        for stat in stats:
            stat_mapped = maps.get_hero_attr(stat)

            # Add stat if not already present
            if stat_mapped not in category_attributes:
                category_attributes[stat_mapped] = {}
            # Add stat if not already present
            if stat_mapped not in category_attributes:
                category_attributes[stat_mapped] = {}

        return category_attributes
