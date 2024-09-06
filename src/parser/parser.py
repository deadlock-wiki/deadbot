import keyvalues3 as kv3
import os
import sys

from parsers import abilities, items, heroes, changelogs

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
        self.abilities_data = kv3.read(abilities_data_path)

    def _load_localizations(self):
        names = json_utils.read(self.DATA_DIR + 'localizations/citadel_gc_english.json')
        descriptions = json_utils.read(self.DATA_DIR + 'localizations/citadel_mods_english.json')
        heroes = json_utils.read(self.DATA_DIR + 'localizations/citadel_heroes_english.json')

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
