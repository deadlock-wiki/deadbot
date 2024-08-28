import keyvalues3 as kv3
import tempfile
import os
import sys

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json


class Parser:
    def __init__(self):
        # constants
        self.DATA_DIR = './decompiled-data/'
        self.OUTPUT_DIR = './output/'

        self._load_localizations()

    def _load_localizations(self):
        self.localizations = dict()

        names = json.read('decompiled-data/localizations/citadel_gc_english.json')
        self.localizations.update(names)

        descriptions = json.read('decompiled-data/localizations/citadel_mods_english.json')
        self.localizations.update(descriptions)

    def run(self):
        self._parse_heroes()
        self._parse_abilities()
        self._parse_items()

    def _parse_heroes(self):
        print('Parsing Heroes...')
        hero_data_path = os.path.join(self.DATA_DIR, 'scripts/heroes.vdata')
        hero_data = kv3.read(hero_data_path)

        attr_map = json.read('attr-maps/hero-map.json')

        hero_keys = hero_data.keys()

        # Base hero stats
        base_hero_stats = hero_data['hero_base']['m_mapStartingStats']

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                merged_stats = dict()

                # Hero specific stats applied over base stats
                hero_stats = hero_data[hero_key]['m_mapStartingStats']
                merged_stats.update(base_hero_stats)
                merged_stats.update(hero_stats)

                merged_stats = self._map_attr_names(merged_stats, attr_map)

                # Add extra data to the hero
                name = self.localizations.get(hero_key, 'Unknown')
                merged_stats['name'] = name

                # create a key associated with the name because of old hero names
                # being used as keys. this will keep a familiar key for usage on the wiki
                merged_stats['key'] = name.lower().replace(' ', '_')

                all_hero_stats[hero_key] = merged_stats

        json.write(self.OUTPUT_DIR + '/hero-data.json', all_hero_stats)

    def _parse_abilities(self):
        print('Parsing Abilities...')
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

        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations.get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write(self.OUTPUT_DIR + '/ability-data.json', all_abilities)

    def _parse_items(self):
        print('Parsing Items...')

    """
        Maps all keys for the set of data to a more human readable ones, defined in /attr-maps
        Any keys that do not have an associated human key are omitted
    """

    def _map_attr_names(self, data, attr_map):
        output_data = dict()
        for key in data:
            if key not in attr_map:
                continue

            human_key = attr_map[key]
            output_data[human_key] = data[key]

        return output_data


if __name__ == '__main__':
    parser = Parser()
    parser.run()
