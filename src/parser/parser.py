import keyvalues3 as kv3
import os
import sys
import tempfile

from parsers import abilities, items, heroes, changelogs

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

# Default method to load vdata files
def _load_vdata_default(vdata_path):
    #print('Starting vdata_path:', vdata_path)
    data = kv3.read(vdata_path+'.vdata')
    out_path = vdata_path.replace('/vdata','')+'.json'
    #print('Finished out_path:', out_path)
    kv3_to_json(data, out_path)
    

    return data



class Parser:
    def __init__(self, language='english'):
        # constants
        self.DATA_DIR = './decompiler/decompiled-data/'
        self.DATA_VDATA_DIR = self.DATA_DIR+'vdata/'
        self.language = language

        self._load_vdata()
        self._load_localizations()

    def _load_vdata(self):
        # Convert .vdata_c to .vdata and .json
        scripts_path = 'scripts'

        # Generic
        self.generic_data = _load_vdata_default(self.DATA_VDATA_DIR+scripts_path+'/generic_data')

        # Hero
        self.hero_data = _load_vdata_default(self.DATA_VDATA_DIR+scripts_path+'/heroes')

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
                kv3_to_json(self.abilities_data, os.path.join(self.DATA_DIR, abilities_subpath+'.json'))

        # Misc
        self.misc_data = _load_vdata_default(self.DATA_VDATA_DIR+scripts_path+'/misc')

    def _load_localizations(self):
        names = json_utils.read(self.DATA_DIR+'localizations/gc/citadel_gc_'+self.language+'.json')
        descriptions = json_utils.read(self.DATA_DIR+'localizations/mods/citadel_mods_'+self.language+'.json')
        heroes = json_utils.read(self.DATA_DIR+'localizations/heroes/citadel_heroes_'+self.language+'.json')

        self.localizations = {'names': names, 'descriptions': descriptions, 'heroes': heroes}

    def run(self):
        print('Parsing...')
        parsed_abilities = self._parse_abilities()
        self._parse_heroes(parsed_abilities)
        self._parse_items()
        self._parse_changelogs()
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

    def _parse_changelogs(self):
        print('Parsing Changelogs...')
        changelogs.ChangelogParser().run_all()


if __name__ == '__main__':
    parser = Parser(language='english')
    parser.run()
