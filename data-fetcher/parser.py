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

        # Initialise master table
        json.write(self.out_dir + 'master-table.json', {})
        self.master_table = json.read(self.out_dir + '/master-table.json')


    def run(self): 
        self.localizations = dict()
        
        names = json.read('decompiled-data/localizations/citadel_gc_english.json')
        self.localizations.update(names)
        
        descriptions = json.read('decompiled-data/localizations/citadel_mods_english.json')
        self.localizations.update(descriptions)
    
        hero_stats = self.parse_heroes()
        self.add_to_master_table(hero_stats)

        ability_stats = self.parse_abilities()
        json.write(self.out_dir + 'master-table.json', self.master_table)

    def parse_heroes(self):
        attr_map = json.read('attr-maps/hero-map.json')

        hero_keys = self.hero_data.keys()

        # Base hero stats
        base_hero_stats = self.hero_data['hero_base']['m_mapStartingStats']

        hero_stats_array = []

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                merged_stats = dict()
            
                # Hero specific stats applied over base stats
                hero_stats = self.hero_data[hero_key]['m_mapStartingStats']
                merged_stats.update(base_hero_stats)
                merged_stats.update(hero_stats)

                merged_stats = self.map_attr_names(merged_stats, attr_map)

                # Add extra data to the hero
                merged_stats['name'] = self.localizations.get(hero_key, 'Unknown')
                merged_stats['key'] = hero_key.replace('hero_', '')

                hero_stats_array.append(merged_stats)

        json.write(self.out_dir + '/hero-data.json', hero_stats_array) 
        return hero_stats_array

    def parse_abilities(self):
        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations.get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write(self.out_dir + '/ability-data.json', all_abilities)


    '''
        Flattens object array and adds it to the master table for easier find and replacement
    '''
    def add_to_master_table(self, array):
        for item in array:
            for item_attr in item:
                # Valve have a lot of mismatched names vs hero keys, we could have a map,
                # but for now we can presume the names are set in stone
                master_key = item['name'].lower() + '#' + item_attr
                
                value = item[item_attr]
                self.master_table[master_key] = value

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
