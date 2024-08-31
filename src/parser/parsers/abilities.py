import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils import json
from constants import OUTPUT_DIR

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

            ability_data = {}

            # ability_data['Name'] = self.localizations['names'].get(ability_key, 'Unknown')
            stats = ability['m_mapAbilityProperties']

            for key in stats:
                stat = stats[key]
                ability_data[key] = stat['m_strValue']

            all_abilities[ability_key] = ability_data

        json.write(OUTPUT_DIR + 'json/ability-data.json', all_abilities)
