import os
import shutil
from .parsers import (
    abilities,
    ability_cards,
    items,
    heroes,
    localizations,
    attributes,
    souls,
    generics,
    npc_units,
)
from utils import json_utils
from loguru import logger
import copy


class Parser:
    def __init__(
        self,
        work_dir,
        output_dir,
        language='english',
        english_only=False,
    ):
        # constants
        self.OUTPUT_DIR = output_dir
        # Directory with decompiled data
        self.DATA_DIR = work_dir

        self.language = language
        self.data = {'scripts': {}}
        self.localization_groups = self._get_localization_groups()

        if english_only:
            self.languages = ['english']
            self.language = 'english'
        else:
            # Get all languages from localization_file i.e. citadel_attributes_english.json -> english
            self.languages = [
                localization_file.split('citadel_' + self.localization_groups[0] + '_')[1].split('.json')[0]
                for localization_file in os.listdir(os.path.join(self.DATA_DIR, 'localizations', self.localization_groups[0]))
            ]

        self._load_vdata()
        self._load_localizations()

        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)
        shutil.copy(f'{self.DATA_DIR}/version.txt', f'{self.OUTPUT_DIR}/version.txt')

    def _get_localization_groups(self):
        # set group priority as some keys are duplicated across groups,
        # where some values have mistakes. Eg. 'mods' has many mistakes and is low priority
        GROUPS = ['main', 'gc', 'gc_mod_names', 'gc_hero_names', 'heroes', 'attributes', 'mods']

        # validate that no groups have been missed from GROUPS
        all_groups = os.listdir(os.path.join(self.DATA_DIR, 'localizations'))
        for group in all_groups:
            # ignore patch_notes since this is handled by the changelog parser
            if group not in GROUPS and group != 'patch_notes':
                raise Exception(f'Missing localization group "{group}" in GROUPS')

        return GROUPS

    def _load_vdata(self):
        # Convert .vdata_c to .vdata and .json
        scripts_path = 'scripts'

        # Load json files to memory
        for file_name in os.listdir(os.path.join(self.DATA_DIR, scripts_path)):
            if file_name.endswith('.json'):
                # path/to/scripts/abilities.json -> abilities
                key = file_name.split('.')[0].split('/')[-1]
                self.data['scripts'][key] = json_utils.read(os.path.join(self.DATA_DIR, scripts_path, file_name))

    def _load_localizations(self):
        """
        Merge all localization groups, including attributes, gc, heroes, main, and mods etc.
        into a single object per language
        """

        self.localizations = {}
        # Start with english language
        for language in ['english'] + self.languages:
            if language not in self.localizations:
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

            # some keys, eg. hero_infernus:n end with ":n"
            # this can interfere with localization, so we should also save it without the ":n"
            if key.endswith(':n'):
                key_without_suffix = key[:-2]
                if key_without_suffix not in self.localizations[language]:
                    self.localizations[language][key_without_suffix] = value

    def run(self):
        logger.trace('Parsing...')
        os.system(f'cp "{self.DATA_DIR}/version.txt" "{self.OUTPUT_DIR}/version.txt"')
        parsed_abilities = self._parse_abilities()
        parsed_heroes = self._parse_heroes(parsed_abilities)
        self._parsed_ability_cards(parsed_heroes)
        self._parse_items()
        self._parse_npcs(parsed_abilities)
        self._parse_attributes()
        self._parse_localizations()
        self._parse_soul_unlocks()
        self._parse_generics()
        logger.trace('Done parsing')

    def _parse_soul_unlocks(self):
        logger.trace('Parsing Soul Unlocks...')
        parsed_soul_unlocks = souls.SoulUnlockParser(self.data['scripts']['heroes']).run()

        json_utils.write(self.OUTPUT_DIR + '/json/soul-unlock-data.json', parsed_soul_unlocks)

    def _parse_generics(self):
        logger.trace('Parsing Generics...')
        generic_data_path = self.OUTPUT_DIR + '/json/generic-data.json'
        parsed_generics = generics.GenericParser(generic_data_path, self.data['scripts']['generic_data']).run()

        json_utils.write(generic_data_path, json_utils.sort_dict(parsed_generics))

    def _parse_localizations(self):
        logger.trace('Parsing Localizations...')
        return localizations.LocalizationParser(self.localizations, self.OUTPUT_DIR).run()

    def _parse_heroes(self, parsed_abilities):
        logger.trace('Parsing Heroes...')
        parsed_heroes, parsed_meaningful_stats = heroes.HeroParser(
            self.data['scripts']['heroes'],
            self.data['scripts']['abilities'],
            parsed_abilities,
            self.localizations[self.language],
        ).run()

        # Ensure it matches the current list of meaningful stats, and raise a warning if not
        path = self.OUTPUT_DIR + '/json/hero-meaningful-stats.json'
        if os.path.exists(path):
            current_meaningful_stats = json_utils.read(path)
            if current_meaningful_stats != parsed_meaningful_stats:
                current_keys = set(current_meaningful_stats.keys())
                new_keys = set(parsed_meaningful_stats.keys())
                logger.warning(
                    'Non-constant stats have changed. '
                    + "Please update [[Module:HeroData]]'s write_hero_comparison_table "
                    + 'lua function for the [[Hero Comparison]] page.'
                    + f'\nAdded keys: {new_keys - current_keys}'
                    + f'\nRemoved keys: {current_keys - new_keys}'
                )

        json_utils.write(
            self.OUTPUT_DIR + '/json/hero-meaningful-stats.json',
            json_utils.sort_dict(parsed_meaningful_stats),
        )

        stripped_heroes = dict()
        # Remove irrelevant data from BoundAbilities in HeroData
        for hero_key, hero_value in copy.deepcopy(parsed_heroes).items():
            bound_abilities = hero_value['BoundAbilities']
            stripped_heroes[hero_key] = hero_value
            stripped_heroes[hero_key]['BoundAbilities'] = {}
            for ability_position, ability_data in bound_abilities.items():
                stripped_heroes[hero_key]['BoundAbilities'][ability_position] = {
                    'Name': ability_data['Name'],
                    'Key': ability_data['Key'],
                }

        json_utils.write(self.OUTPUT_DIR + '/json/hero-data.json', json_utils.sort_dict(stripped_heroes))
        return parsed_heroes

    def _parse_abilities(self):
        logger.trace('Parsing Abilities...')
        parsed_abilities = abilities.AbilityParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['heroes'],
            self.localizations[self.language],
        ).run()

        stripped_abilities = {}
        for key, ability in parsed_abilities.items():
            # Exclude Patron from being written to the public json to prevent it being tagged as a Hero Ability
            if ability.get('Name') == 'Patron':
                continue

            stripped_abilities[key] = json_utils.strip_zeroes(ability)

        json_utils.write(self.OUTPUT_DIR + '/json/ability-data.json', json_utils.sort_dict(stripped_abilities))
        return parsed_abilities

    def _parsed_ability_cards(self, parsed_heroes):
        logger.trace('Parsing Ability UI...')

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
        logger.trace('Parsing Items...')
        (parsed_items, item_component_chart) = items.ItemParser(
            self.data['scripts']['abilities'],
            self.data['scripts']['generic_data'],
            self.localizations[self.language],
        ).run()

        json_utils.write(self.OUTPUT_DIR + '/json/item-data.json', json_utils.sort_dict(parsed_items))

        with open(self.OUTPUT_DIR + '/item-component-tree.txt', 'w') as f:
            f.write(str(item_component_chart))

    def _parse_npcs(self, parsed_abilities):
        logger.trace('Parsing NPCs...')
        parsed_npcs = npc_units.NpcParser(
            npc_units_data=self.data['scripts']['npc_units'],
            modifiers_data=self.data['scripts']['modifiers'],
            misc_data=self.data['scripts']['misc'],
            localizations=self.localizations[self.language],
            abilities_data=self.data['scripts']['abilities'],
        ).run()

        json_utils.write(self.OUTPUT_DIR + '/json/npc-data.json', json_utils.sort_dict(parsed_npcs))

    def _parse_attributes(self):
        logger.trace('Parsing Attributes...')
        (parsed_attributes, attribute_orders) = attributes.AttributeParser(self.data['scripts']['heroes'], self.localizations[self.language]).run()

        json_utils.write(self.OUTPUT_DIR + '/json/attribute-data.json', parsed_attributes)
        json_utils.write(self.OUTPUT_DIR + '/json/stat-infobox-order.json', attribute_orders)
