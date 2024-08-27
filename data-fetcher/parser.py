import keyvalues3 as kv3
import tempfile
import os
from utils import json

class Parser:
    def __init__(self):
        self.data_dir = './decompiled-data/'
        self.hero_data_path = os.path.join(self.data_dir, 'scripts/heroes.vdata')
        self.abilities_data_path = os.path.join(self.data_dir , 'scripts/abilities.vdata')
        with open(self.abilities_data_path, 'r') as f:
            content = f.read()
            # replace 'subclass:' with ''
            # subclass features in kv3 don't seem to be supported in the keyvalues3 python library
            content = content.replace('subclass:', '')
            # write new content to tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                tf.write(content)
                self.abilities_data = kv3.read(tf.name)


        self.hero_data = kv3.read(os.path.join(self.data_dir, 'scripts/heroes.vdata'))

    def run(self): 
        self.localizations = dict()
        
        names = json.read('localizations/citadel_gc_english.json')
        self.localizations.update(names)
        
        descriptions = json.read('localizations/citadel_mods_english.json')
        self.localizations.update(descriptions)
    
        self.parse_heroes()
        self.parse_abilities()

    def parse_heroes(self):
        hero_keys = self.hero_data.keys()

        # Base hero stats
        base_hero_stats = self.hero_data['hero_base']['m_mapStartingStats']

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                merged_stats = dict()

                merged_stats['name'] = self.localizations.get(hero_key, 'Unknown')

                # Hero specific stats applied over base stats
                hero_stats = self.hero_data[hero_key]['m_mapStartingStats']
                merged_stats.update(base_hero_stats)
                merged_stats.update(hero_stats)

                all_hero_stats[hero_key] = merged_stats

        json.write('output/hero-data.json', all_hero_stats) 
    
    def parse_abilities(self):
        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations.get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write('output/ability-data.json', all_abilities)


if __name__ == "__main__":
    parser = Parser() 
    parser.run()  
