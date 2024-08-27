import keyvalues3 as kv3
import tempfile
import os
from utils import json

class Parser:
    def __init__(self):
        self.data_dir = './decompiled-data/'
        self.out_dir = './output/'
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
        
        names = json.read('decompiled-data/localizations/citadel_gc_english.json')
        self.localizations.update(names)
        
        descriptions = json.read('decompiled-data/localizations/citadel_mods_english.json')
        self.localizations.update(descriptions)
    
        hero_stats = self.parse_heroes()
        ability_stats = self.parse_abilities()

    def parse_heroes(self):
        attr_map = json.read('attr-maps/hero-map.json')

        hero_keys = self.hero_data.keys()

        # Base hero stats
        base_hero_stats = self.hero_data['hero_base']['m_mapStartingStats']

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                merged_stats = dict()

                # Hero specific stats applied over base stats
                hero_stats = self.hero_data[hero_key]['m_mapStartingStats']
                merged_stats.update(base_hero_stats)
                merged_stats.update(hero_stats)

                merged_stats = self.map_attr_names(merged_stats, attr_map)

                # Add extra data to the hero
                name = self.localizations.get(hero_key, 'Unknown')
                merged_stats['name'] = name
                
                # create a key associated with the name because of old hero names 
                # being used as keys. this will keep a familiar key for usage on the wiki
                merged_stats['key'] = name.lower().replace(' ', '_')
                
                all_hero_stats[hero_key] = merged_stats

        json.write(self.out_dir + '/hero-data.json', all_hero_stats) 

    def parse_abilities(self):
        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations.get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write(self.out_dir + '/ability-data.json', all_abilities)

    '''
        Maps all keys for the set of data to a more human readable ones, defined in /attr-maps
        Any keys that do not have an associated human key are omitted
    '''
    def map_attr_names(self, data, attr_map):
        output_data = dict()
        for key in data:
            if key not in attr_map:
                continue
            
            human_key = attr_map[key]
            output_data[human_key] = data[key]

        return output_data
        
if __name__ == "__main__":
    parser = Parser() 
    parser.run()  
