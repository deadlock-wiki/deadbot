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
        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations['names'].get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write(OUTPUT_DIR + 'json/ability-data.json', all_abilities)
