import keyvalues3 as kv3
import tempfile
import os
import sys

from parsers import abilities, items, heroes

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils


class Parser:
    def __init__(self, language='english'):
        # constants
        self.DATA_DIR = './decompiled-data/'
        self.language = language

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
        names = json_utils.read(
            'decompiled-data/localizations/gc/citadel_gc_' + self.language + '.json'
        )
        descriptions = json_utils.read(
            'decompiled-data/localizations/mods/citadel_mods_' + self.language + '.json'
        )
        heroes = json_utils.read(
            'decompiled-data/localizations/heroes/citadel_heroes_' + self.language + '.json'
        )

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
        return abilities.AbilityParser(self.abilities_data, self.localizations).run()

    def _parse_items(self):
        print('Parsing Items...')
        items.ItemParser(self.abilities_data, self.generic_data, self.localizations).run()


if __name__ == '__main__':
    parser = Parser(language='english')
    parser.run()
