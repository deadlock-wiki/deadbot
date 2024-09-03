import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from constants import OUTPUT_DIR
import utils.json_utils as json_utils
import utils.string_utils as string_utils


class AbilityParser:
    def __init__(self, abilities_data, localizations):
        self.abilities_data = abilities_data
        self.localizations = localizations

    def run(self):
        all_abilities = {}

        for ability_key in self.abilities_data:
            ability = self.abilities_data[ability_key]
            if type(ability) is not dict:
                continue

            if 'm_eAbilityType' not in ability:
                continue

            if ability['m_eAbilityType'] != 'EAbilityType_Signature':
                continue

            ability_data = {
                'Name': self.localizations['heroes'].get(ability_key, None),
            }

            stats = ability['m_mapAbilityProperties']

            for key in stats:
                stat = stats[key]
                ability_data[key] = stat['m_strValue']

            description = (self.localizations['heroes'].get(ability_key + '_desc'),)
            ability_data['Description'] = string_utils.format_description(description, ability_data)

            all_abilities[ability_key] = json_utils.sort_dict(ability_data)

        json_utils.write(OUTPUT_DIR + 'json/ability-data.json', json_utils.sort_dict(all_abilities))
