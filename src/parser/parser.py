import keyvalues3 as kv3
import tempfile
import os
import sys
import re

from parsers import abilities, items, heroes

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json

class Parser:
    def __init__(self):
        # constants
        self.DATA_DIR = './decompiled-data/'

        self._load_vdata()
        self._load_localizations()

    def _load_vdata(self):
        generic_data_path = os.path.join(self.DATA_DIR, 'scripts/generic_data.vdata')
        self.generic_data = kv3.read(generic_data_path)

        hero_data_path = os.path.join(self.DATA_DIR, 'scripts/heroes.vdata')
        self.hero_data = kv3.read(hero_data_path)

        abilities_data_path = os.path.join(self.DATA_DIR, 'scripts/abilities.vdata')

        with open(abilities_data_path, 'r') as f:
            content = f.read()
            # replace 'subclass:' with ''
            # subclass features in kv3 don't seem to be supported in the keyvalues3 python library
            content = content.replace('subclass:', '')
            # write new content to tempfilex
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                tf.write(content)
                self.abilities_data = kv3.read(tf.name)

    def _load_localizations(self):
        names = json.read('decompiled-data/localizations/citadel_gc_english.json')

        descriptions = json.read('decompiled-data/localizations/citadel_mods_english.json')
        self.localizations = {
            'names': names,
            'descriptions': descriptions,
        }

    def run(self):
        print('Parsing...')
        self._parse_heroes()
        self._parse_abilities()
        self._parse_items()
        print('Done parsing')

    def _parse_heroes(self):
        print('Parsing Heroes...')
        heroes.HeroParser(self.hero_data, self.abilities_data, self.localizations).run()

    def _parse_abilities(self):
        print('Parsing Abilities...')   
        abilities.AbilityParser(self.abilities_data, self.localizations).run()

    def _parse_items(self):
        print('Parsing Items...')
        items.ItemParser(self.abilities_data, self.generic_data, self.localizations).run()

if __name__ == '__main__':
    parser = Parser()
    parser.run()
