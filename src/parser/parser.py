import os
import sys

from parsers import abilities, items, heroes, changelogs, localizations, attributes

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils


class Parser:
    def __init__(self, language='english'):
        # constants
        self.DATA_DIR = os.getenv('WORK_DIR',"./decompiled-data")
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
        for file_name in os.listdir(os.path.join(self.DATA_DIR,scripts_path)):
            if file_name.endswith('.json'):
                # path/to/scripts/abilities.json -> abilities
                key = file_name.split('.')[0].split('/')[-1]
                self.data['scripts'][key] = json_utils.read(
                    os.path.join(self.DATA_DIR, scripts_path, file_name)
                )

    def _load_localizations(self):
        """
        Merge all localization groups, including attributes, gc, heroes, main, and mods etc.
        into a single object per language
        """

        self.localizations = {}
        for language in self.languages:
            self.localizations[language] = {}
            for localization_group in self.localization_groups:
                localization_data = json_utils.read( os.path.join(
                    self.DATA_DIR,
                    'localizations/',
                    localization_group,
                    'citadel_' + localization_group + '_' + language + '.json'
                )
                )

                self._merge_localizations(language, localization_data)

    def _merge_localizations(self, language, data):
        """
        Assigns a set of localization data to self.localizations for use across the parser

        Args:
            language (str): language for the provided data
            data (dict): contents of a group of localization data for the given language
                Eg. contents of citadels_heroes_danish.json
        """
        for key, value in data.items():
            # Skip language key, and potentially others down the line
            # that are not needed but shared across groups
            if key in ['Language']:
                continue

            if key not in self.localizations[language]:
                self.localizations[language][key] = value
            else:
                current_value = self.localizations[language][key]
                raise Exception(
                    f'Key {key} with value {value} already exists in {language} localization '
                    + f'data with value {current_value}.'
                )

    def run(self):
        print('Parsing...')
        self._parse_localizations()
        parsed_abilities = self._parse_abilities()
        self._parse_heroes(parsed_abilities)
        self._parse_items()
        self._parse_attributes()
        self._parse_changelogs()
        print('Done parsing')

    def _parse_localizations(self):
        print('Parsing Localizations...')

        # TODO
        return localizations.LocalizationParser(self.localizations).run()

    def _parse_heroes(self, parsed_abilities):
        print('Parsing Heroes...')
        return heroes.HeroParser(
            self.data['scripts']['heroes'],
            self.data['scripts']['abilities'],
            parsed_abilities,
            self.localizations[self.language],
        ).run()

    def _parse_abilities(self):
        print('Parsing Abilities...')
        return abilities.AbilityParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['heroes'],
            self.localizations[self.language],
        ).run()

    def _parse_items(self):
        print('Parsing Items...')
        items.ItemParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['generic_data'],
            self.localizations[self.language],
        ).run()

    def _parse_attributes(self):
        print('Parsing Attributes...')
        attributes.AttributeParser(
            self.data['scripts']['heroes'], self.localizations[self.language]
        ).run()

    def _parse_changelogs(self):
        print('Parsing Changelogs...')
        changelogs.ChangelogParser().run_all()


if __name__ == '__main__':
    parser = Parser()
    parser.run()
