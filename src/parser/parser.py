import os
import sys

from parsers import abilities, items, heroes, changelogs, localizations, attributes
import re

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils
from parsers.constants import OUTPUT_DIR

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
        """
        Merge all localization groups, including attributes, gc, heroes, main, and mods etc.
        into a single object per language
        """

        self.localizations = {}
        for language in self.languages:
            self.localizations[language] = {}
            for localization_group in self.localization_groups:
                localization_data = json_utils.read(
                    self.DATA_DIR
                    + 'localizations/'
                    + localization_group
                    + '/citadel_'
                    + localization_group
                    + '_'
                    + language
                    + '.json'
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
        parsed_heroes, hero_non_constants = self._parse_heroes(parsed_abilities)
        self._parse_items()
        parsed_attributes, attribute_orders = self._parse_attributes()
        self._parse_changelogs()
        self._write_stat_comparison_list(parsed_attributes, hero_non_constants, attribute_orders)
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
        return attributes.AttributeParser(
            self.data['scripts']['heroes'], self.localizations[self.language]
        ).run()

    def _parse_changelogs(self):
        print('Parsing Changelogs...')
        changelogs.ChangelogParser().run_all()

    def _write_stat_comparison_list(self, parsed_attributes, hero_non_constants, attribute_orders):
        """
        Congolmerate stat-related data to a list used to generate deadlocked.wiki/Hero_Comparison page
        """
        # A function I spent too many failed attempts on writing on the frontend
        # Encourage any readers to attempt it, then remove this function if succeeded

        # hero_non_constants looks like ['DPS', 'SustainedDPS', 'MaxHealth', etc.]
        # parsed_attributes looks like {'Weapon': {'DPS': {'label': 'key_to_localize_dps'
        # attribute_orders looks like {'Weapon': 'attribute_order': ['DPS', 'SustainedDPS', 'MaxHealth', etc.]}

        # Hero Comparison table needs to 
        # - include only and stats that are in hero_non_constants
        # - if its in attribute_orders, use its order
        # - if its in parsed_attributes, use its label, else use the key

        # stats_to_include looks like {'Weapon': {'DPS': {'label': 'key_to_localize_dps'

        stats_to_include = {}

        # Add stats from parsed_attributes
        for non_constant in hero_non_constants:
            for category, attributes in parsed_attributes.items():
                for attribute, data in attributes.items():
                    if non_constant == attribute:
                        if category not in stats_to_include:
                            stats_to_include[category] = {}
                        stats_to_include[category][attribute] = data

        # Add stats from hero_non_constants to "Weapon" category that are not in parsed_attributes and not already in hero_non_constants in any category, use key as label
        for non_constant in hero_non_constants:
            found = False
            for category, attributes in parsed_attributes.items():
                if non_constant in attributes:
                    found = True
                    break

            if not found:
                if 'Weapon' not in stats_to_include:
                    stats_to_include['Weapon'] = {}
                print(non_constant)
                # non-constants that will be included but don't have localization
                label = ""
                postfix = ""
                if non_constant.startswith('Falloff'):
                    postfix = 'StatDesc_WeaponRangeFalloffMax_postfix'
                if non_constant == 'SustainedDPS':
                    label = 'DPS_label'
                    postfix = 'DPS_postfix'
                if non_constant == 'ReloadDelay':
                    label = 'StatDesc_ReloadTime'
                    postfix = 'StatDesc_ReloadTime_postfix'

                if label == "":
                    # Use key, but with spaces before capital letters using regex
                    label = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', non_constant)


                stats_to_include['Weapon'][non_constant] = {}
                stats_to_include['Weapon'][non_constant]['label'] = label
                if postfix:
                    stats_to_include['Weapon'][non_constant]['postfix'] = postfix


        # Within each category, add the order from attribute_order for each attribute to key "attribute_order". 
        # If the attribute isnt in attribute_order, insert them in the list in alphabetical order
        for category, attributes in stats_to_include.items():
            if category in attribute_orders:
                stats_to_include[category]['attribute_order'] = attribute_orders[category]['attribute_order']
                for attribute in list(attributes.keys()):
                    if attribute not in attribute_orders[category]:
                        stats_to_include[category]['attribute_order'].append(attribute)

        # Remove non-distinct elements from each attribute order
        for category, attributes in stats_to_include.items():
            if 'attribute_order' in attributes:
                stats_to_include[category]['attribute_order'] = list(dict.fromkeys(attributes['attribute_order']))

        # Move DPS and SustainedDPS to the front of the weapon category list
        move_to_front = ['SustainedDPS', 'DPS']
        if 'Weapon' in stats_to_include:
            for stat in move_to_front:
                if stat in stats_to_include['Weapon']:
                    stats_to_include['Weapon']['attribute_order'].remove(stat)
                    stats_to_include['Weapon']['attribute_order'].insert(0, stat)
        
        # Write the attributes to a json file
        json_utils.write(OUTPUT_DIR + 'json/hero-non-constants.json', stats_to_include)

if __name__ == '__main__':
    parser = Parser()
    parser.run()
