import keyvalues3 as kv3
import os
import sys
import tempfile

from parsers import abilities, items, heroes, changelogs

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils


class Parser:
    def __init__(self, language='english'):
        # constants
        self.DATA_DIR = './decompiler/decompiled-data/'
        self.language = language
        self.data = {'scripts': {}}

        self.localization_groups = os.listdir(os.path.join(self.DATA_DIR, 'localizations'))
        # Get all languages from localization_file i.e. citadel_attributes_english.json -> english
        self.languages = [
            localization_file.split('citadel_' + self.localization_groups[0] + '_')[1].split(
                '.json'
            )[0]
            for localization_file in os.listdir(
                os.path.join(self.DATA_DIR, 'localizations/' + self.localization_groups[0])
            )
        ]

        self._load_vdata()
        self._load_localizations()

    def _load_vdata(self):
        # Convert .vdata_c to .vdata and .json
        scripts_path = 'scripts'

        # Load json files to memory
        for file_name in os.listdir(self.DATA_DIR + scripts_path):
            if file_name.endswith('.json'):
                # path/to/scripts/abilities.json -> abilities
                key = file_name.split('.')[0].split('/')[-1]
                self.data['scripts'][key] = json_utils.read(
                    os.path.join(self.DATA_DIR, scripts_path, file_name)
                )

    def _load_localizations(self):
        # Load all localizations data to memory

        # Level 1: language
        # Level 2: localization_group (i.e. attributes, gc, heroes, main, mods)
        # Level 3: localization key
        # Level 4: localized text
        self.localizations = {}
        for language in self.languages:
            self.localizations[language] = {}
            for localization_group in self.localization_groups:
                localization_group_data = json_utils.read(
                    self.DATA_DIR
                    + 'localizations/'
                    + localization_group
                    + '/citadel_'
                    + localization_group
                    + '_'
                    + language
                    + '.json'
                )
                self.localizations[language][localization_group] = localization_group_data

    def run(self):
        print('Parsing...')
        parsed_localizations = self._parse_localizations()
        parsed_abilities = self._parse_abilities()
        self._parse_heroes(parsed_abilities)
        self._parse_items()
        self._parse_changelogs()
        print('Done parsing')

    def _parse_localizations(self):
        print('Parsing Localizations...')
        # TODO
        # return localization.LocalizationsParser(
        #     self.data['scripts']['localizations'],
        #     self.localizations,
        # ).run()

    def _parse_heroes(self, parsed_abilities):
        print('Parsing Heroes...')
        heroes.HeroParser(
            self.data['scripts']['heroes'],
            self.data['scripts']['abilities'],
            parsed_abilities,
            self.localizations[self.language],
        ).run()

    def _parse_abilities(self):
        print('Parsing Abilities...')
        return abilities.AbilityParser(
            self.data['scripts']['abilities'], self.localizations[self.language]
        ).run()

    def _parse_items(self):
        print('Parsing Items...')
        items.ItemParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['generic_data'],
            self.localizations[self.language],
        ).run()

    def _parse_changelogs(self):
        print('Parsing Changelogs...')
        changelogs.ChangelogParser().run_all()


if __name__ == '__main__':
    parser = Parser()
    parser.run()
