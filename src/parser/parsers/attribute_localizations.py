import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import utils.json_utils as json_utils
import utils.string_utils as string_utils
from parsers.abilities import _get_upgrade_data

from .constants import OUTPUT_DIR

class AttributeLocalizationParser:
    def __init__(self, ability_data, localization_data):
        self.ability_data = ability_data
        self.localization_data = localization_data
        self.attribute_map = {}

    def run(self):
        upgrade_data = _get_upgrade_data(self.ability_data)

        for upgrade_key, upgrade_value in upgrade_data.items():
            if 'm_mapAbilityProperties' in upgrade_value:
                for ability_property_key, ability_property_value in upgrade_value['m_mapAbilityProperties'].items():
                    if ability_property_key not in self.attribute_map:

                        if 'm_eDisplayType' in ability_property_value:
                            attribute_key = ability_property_value['m_eDisplayType']
                            attribute_value = ability_property_key

                            # Track # of occurrences of each attribute to its translated localized string
                            if attribute_key not in self.attribute_map:
                                self.attribute_map[attribute_key] = {}

                            if attribute_value in self.attribute_map[attribute_key]:
                                self.attribute_map[attribute_key][attribute_value] += 1
                            else:
                                self.attribute_map[attribute_key][attribute_value] = 1

        #print(self.attribute_map)

        json_utils.write(OUTPUT_DIR + 'json/attribute-localization-data.json', json_utils.sort_dict(self.attribute_map))