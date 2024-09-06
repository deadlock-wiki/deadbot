import keyvalues3 as kv3
import tempfile
import os
import sys

from parsers import abilities, items, heroes

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils

# Recursively accesses all nested objects and hosts json-serializable values in the returned dict
def kv3_to_dict(kv3_obj):
    # Include all items that are dicts
    dict = {}

    # If cannot access attributes, end recursion
    try:
        items = kv3_obj.items()
    except AttributeError:
        return None
    
    for key, value in items:
        if not json_utils.is_json_serializable(value): # Only include values that are json serializable
            try:
                value = kv3_to_dict(value)
                if value is None:
                    continue # Continue to next value if its not serializable
            except TypeError:
                return None

        dict[key] = value

    return dict


# Converts kv3 object to dict, then writes dict to json
def kv3_to_json(kv3_obj, output_file):
    # output_file should always end in .json
    if not output_file.endswith('.json'):
        raise ValueError('output_file must end in .json')
    
    return json_utils.write(output_file, kv3_to_dict(kv3_obj))

class Parser:
    def __init__(self, language='english'):
        # constants
        self.DATA_VDATA_DIR = './decompiled-data/vdata/'
        self.DATA_JSON_DIR = './decompiled-data/json/'
        self.language = language

        self._load_vdata()
        self._load_localizations()

    def _load_vdata(self):
        # Convert .vdata_c to .vdata and .json
        # Generic
        scripts_path = 'scripts'
        generic_subpath = os.path.join(scripts_path, 'generic_data')
        generic_data_path = os.path.join(self.DATA_VDATA_DIR, generic_subpath+'.vdata')
        self.generic_data = kv3.read(generic_data_path)
        kv3_to_json(self.generic_data, os.path.join(self.DATA_JSON_DIR, generic_subpath+'.json'))

        # Hero
        hero_subpath = os.path.join(scripts_path, 'heroes')
        hero_data_path = os.path.join(self.DATA_VDATA_DIR, hero_subpath+'.vdata')
        self.hero_data = kv3.read(hero_data_path)
        kv3_to_json(self.hero_data, os.path.join(self.DATA_JSON_DIR, hero_subpath+'.json'))

        # Abilities
        abilities_subpath = os.path.join(scripts_path, 'abilities')
        abilities_data_path = os.path.join(self.DATA_VDATA_DIR, abilities_subpath+'.vdata')
        with open(abilities_data_path, 'r') as f:
            content = f.read()
            # replace 'subclass:' with ''
            # subclass features in kv3 don't seem to be supported in the keyvalues3 python library
            content = content.replace('subclass:', '')
            # write new content to tempfilex
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                tf.write(content)
                self.abilities_data = kv3.read(tf.name)
                kv3_to_json(self.abilities_data, os.path.join(self.DATA_JSON_DIR, abilities_subpath+'.json'))

    def _load_localizations(self):
        names = json_utils.read('decompiled-data/json/localizations/gc/citadel_gc_'+self.language+'.json')
        descriptions = json_utils.read('decompiled-data/json/localizations/mods/citadel_mods_'+self.language+'.json')
        heroes = json_utils.read('decompiled-data/json/localizations/heroes/citadel_heroes_'+self.language+'.json')

        self.localizations = {'names': names, 'descriptions': descriptions, 'heroes': heroes}

    def run(self):
        print('Parsing...')
        parsed_abilities = self._parse_abilities()
        self._parse_heroes(parsed_abilities)
        self._parse_items()
        print('Done parsing')

    def _parse_heroes(self, parsed_abilities):
        print('Parsing Heroes...')
        heroes.HeroParser(
            self.hero_data, self.abilities_data, parsed_abilities, self.localizations
        ).run()

    def _parse_abilities(self):
        print('Parsing Abilities...')
        ability_keys = self.abilities_data.keys()
        filtered_keys = [key for key in ability_keys if not key.startswith('upgrade_')]
        #print(filtered_keys)
        return abilities.AbilityParser(self.abilities_data, self.localizations).run()

    def _parse_items(self):
        print('Parsing Items...')
        items.ItemParser(self.abilities_data, self.generic_data, self.localizations).run()


if __name__ == '__main__':
    parser = Parser(language='english')
    #parser = Parser(language='english')
    parser.run()
