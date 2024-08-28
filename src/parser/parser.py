import keyvalues3 as kv3
import tempfile
import os
import sys
from python_mermaid.diagram import MermaidDiagram, Node, Link
import maps

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json

nodes = []
links = []


class Parser:
    def __init__(self):
        # constants
        self.DATA_DIR = './decompiled-data/'
        self.OUTPUT_DIR = './output/'

        self._load_files()
        self._load_localizations()

    def _load_files(self):
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
        # self._parse_heroes()
        # self._parse_abilities()
        self._parse_items()
        print('Done parsing')

        chart = MermaidDiagram(title='Items', nodes=nodes, links=links)

        with open(self.OUTPUT_DIR + '/item-component-tree.txt', 'w') as f:
            f.write(str(chart))

    def _parse_heroes(self):
        print('Parsing Heroes...')
        attr_map = json.read('attr-maps/hero-map.json')

        hero_keys = self.hero_data.keys()

        # Base hero stats
        base_hero_stats = self.hero_data['hero_base']['m_mapStartingStats']

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                merged_stats = dict()

                # Hero specific stats applied over base stats
                hero_stats = self.hero_data[hero_key]['m_mapStartingStats']
                merged_stats.update(base_hero_stats)
                merged_stats.update(hero_stats)

                merged_stats = self._map_attr_names(merged_stats, attr_map)

                # Add extra data to the hero
                name = self.localizations['names'].get(hero_key, 'Unknown')
                merged_stats['name'] = name

                # create a key associated with the name because of old hero names
                # being used as keys. this will keep a familiar key for usage on the wiki
                merged_stats['key'] = name.lower().replace(' ', '_')

                all_hero_stats[hero_key] = merged_stats

        json.write(self.OUTPUT_DIR + '/hero-data.json', all_hero_stats)

    def _parse_abilities(self):
        print('Parsing Abilities...')

        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations['names'].get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write(self.OUTPUT_DIR + '/ability-data.json', all_abilities)

    def _parse_items(self):
        print('Parsing Items...')

        item_keys = [key for key in self.abilities_data if key.startswith('upgrade_')]  #

        all_items = {}
        missing_types = []
        for key in item_keys:
            item_value = self.abilities_data[key]
            item_ability_attrs = item_value['m_mapAbilityProperties']

            # Assign target types array
            target_types = []
            if 'm_nAbilityTargetTypes' in item_value:
                for target_type in item_value['m_nAbilityTargetTypes'].split('|'):
                    # strip all whitespace
                    target_type = target_type.replace(' ', '')
                    if target_type == '':
                        continue
                    mapped_type = maps.TARGET_TYPE[target_type]
                    target_types.append(mapped_type)

            parsed_item_data = {
                'Key': key,
                'Name': self.localizations['names'].get(key),
                'Description': self.localizations['descriptions'].get(key),
                'Slot': maps.SLOT_TYPE.get(item_value.get('m_eItemSlotType'), 'None'),
                'Tier': maps.TIER.get(item_value.get('m_iItemTier'), 'None'),
                # 'ImagePath': str(item_value.get('m_strAbilityImage', 'None')),
                'TargetTypes': target_types,
            }

            for attr_key in item_ability_attrs.keys():
                # "Ability" prefix on attr names is redundant
                new_key = (
                    attr_key.replace('Ability', '') if attr_key.startswith('Ability') else attr_key
                )
                parsed_item_data[new_key] = item_ability_attrs[attr_key]['m_strValue']

            if 'm_vecComponentItems' in item_value:
                parsed_item_data['Components'] = item_value['m_vecComponentItems']
                self._add_children_to_tree(parsed_item_data['Name'], parsed_item_data['Components'])

            all_items[key.replace('upgrade_', '')] = parsed_item_data

        json.write(self.OUTPUT_DIR + '/item-data.json', all_items)
        print(missing_types)

    # Add items to mermaid tree
    def _add_children_to_tree(self, parent_key, child_keys):
        for child_key in child_keys:
            links.append(Link(Node(self.localizations['names'].get(child_key)), Node(parent_key)))

    """
        Maps all keys for the set of data to a more human readable ones, defined in /attr-maps
        Any keys that do not have an associated human key are omitted
    """

    def _map_attr_names(self, data, attr_map):
        output_data = dict()
        for key in data:
            if key not in attr_map:
                continue

            value = data[key]

            human_key = attr_map[key]
            output_data[human_key] = value

        return output_data


if __name__ == '__main__':
    parser = Parser()
    parser.run()
