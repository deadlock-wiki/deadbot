import os
import shutil
from .parsers import abilities, ability_cards, items, heroes, localizations, attributes, souls
from utils import json_utils


class Parser:
    def __init__(
        self,
        work_dir,
        output_dir,
        language='english',
    ):
        # constants
        self.OUTPUT_DIR = output_dir
        # Directory with decompiled data
        self.DATA_DIR = work_dir

        self.language = language
        self.data = {'scripts': {}}
        self.localization_groups = os.listdir(os.path.join(self.DATA_DIR, 'localizations'))
        # Get all languages from localization_file i.e. citadel_attributes_english.json -> english
        self.languages = [
            localization_file.split('citadel_' + self.localization_groups[0] + '_')[1].split(
                '.json'
            )[0]
            for localization_file in os.listdir(
                os.path.join(self.DATA_DIR, 'localizations', self.localization_groups[0])
            )
        ]

        self._load_vdata()
        self._load_localizations()

        shutil.copy(f'{self.DATA_DIR}/version.txt', f'{self.OUTPUT_DIR}/version.txt')

    def _load_vdata(self):
        # Convert .vdata_c to .vdata and .json
        scripts_path = 'scripts'

        # Load json files to memory
        for file_name in os.listdir(os.path.join(self.DATA_DIR, scripts_path)):
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
                localization_data = json_utils.read(
                    os.path.join(
                        self.DATA_DIR,
                        'localizations/',
                        localization_group,
                        'citadel_' + localization_group + '_' + language + '.json',
                    )
                )

                self._merge_localizations(language, localization_group, localization_data)

    def _merge_localizations(self, language, group, data):
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

            # 'heroes' group is storing extra English labels for each language, causing it to throw
            # duplicate key error. This is a temporary measure to keep patch updates going
            elif group != 'heroes':
                current_value = self.localizations[language][key]
                print(
                    f'Key {key} with value {value} already exists in {language} localization '
                    + f'data with value {current_value}.'
                )

    def run(self):
        print('Parsing...')
        os.system(f'cp "{self.DATA_DIR}/version.txt" "{self.OUTPUT_DIR}/version.txt"')
        parsed_abilities = self._parse_abilities()
        parsed_heroes = self._parse_heroes(parsed_abilities)
        self._parsed_ability_cards(parsed_heroes)
        self._parse_items()
        self._parse_attributes()
        self._parse_localizations()
        self._parse_soul_unlocks()
        print('Done parsing')

    def _parse_soul_unlocks(self):
        print('Parsing Soul Unlocks...')
        parsed_soul_unlocks = souls.SoulUnlockParser(self.data['scripts']['heroes']).run()

        json_utils.write(self.OUTPUT_DIR + '/json/soul-unlock-data.json', parsed_soul_unlocks)

    def _parse_localizations(self):
        print('Parsing Localizations...')
        return localizations.LocalizationParser(self.localizations, self.OUTPUT_DIR).run()

    def _parse_heroes(self, parsed_abilities):
        print('Parsing Heroes...')
        parsed_heroes, parsed_meaningful_stats = heroes.HeroParser(
            self.data['scripts']['heroes'],
            self.data['scripts']['abilities'],
            parsed_abilities,
            self.localizations[self.language],
        ).run()

        # Ensure it matches the current list of meaningful stats, and raise a warning if not
        # File diff will also appear in git
        if not json_utils.compare_json_file_to_dict(
            self.OUTPUT_DIR + '/json/hero-meaningful-stats.json', parsed_meaningful_stats
        ):
            print(
                'Warning: Non-constant stats have changed. '
                + "Please update [[Module:HeroData]]'s write_hero_comparison_table "
                + 'lua function for the [[Hero Comparison]] page.'
            )

        json_utils.write(
            self.OUTPUT_DIR + '/json/hero-meaningful-stats.json',
            json_utils.sort_dict(parsed_meaningful_stats),
        )

        json_utils.write(
            self.OUTPUT_DIR + '/json/hero-data.json', json_utils.sort_dict(parsed_heroes)
        )
        return parsed_heroes

    def _parse_abilities(self):
        print('Parsing Abilities...')
        parsed_abilities = abilities.AbilityParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['heroes'],
            self.localizations[self.language],
        ).run()

        json_utils.write(
            self.OUTPUT_DIR + '/json/ability-data.json', json_utils.sort_dict(parsed_abilities)
        )
        return parsed_abilities

    def _parsed_ability_cards(self, parsed_heroes):
        print('Parsing Ability UI...')

        for language in self.languages:
            (parsed_ability_cards, changed_localizations) = ability_cards.AbilityCardsParser(
                self.data['scripts']['abilities'],
                parsed_heroes,
                language,
                self.localizations,
            ).run()

            self.localizations[language].update(changed_localizations)

            # Only write to ability_cards.json for English
            if language == 'english':
                json_utils.write(self.OUTPUT_DIR + '/json/ability-cards.json', parsed_ability_cards)

    def _parse_items(self):
        print('Parsing Items...')
        (parsed_items, item_component_chart) = items.ItemParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['generic_data'],
            self.localizations[self.language],
        ).run()

        json_utils.write(
            self.OUTPUT_DIR + '/json/item-data.json', json_utils.sort_dict(parsed_items)
        )

        with open(self.OUTPUT_DIR + '/item-component-tree.txt', 'w') as f:
            f.write(str(item_component_chart))

    def _parse_attributes(self):
        print('Parsing Attributes...')
        (parsed_attributes, attribute_orders) = attributes.AttributeParser(
            self.data['scripts']['heroes'], self.localizations[self.language]
        ).run()

        json_utils.write(self.OUTPUT_DIR + '/json/attribute-data.json', parsed_attributes)
        json_utils.write(self.OUTPUT_DIR + '/json/stat-infobox-order.json', attribute_orders)
