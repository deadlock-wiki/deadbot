import keyvalues3 as kv3
import tempfile
import os
import sys
import re
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
        self.OUTPUT_DIR = '../../output-data/'

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

        chart = MermaidDiagram(title='Items', nodes=nodes, links=links)

        with open(self.OUTPUT_DIR + '/item-component-tree.txt', 'w') as f:
            f.write(str(chart))

    def _parse_heroes(self):
        print('Parsing Heroes...')
        hero_keys = self.hero_data.keys()

        all_hero_stats = dict()

        for hero_key in hero_keys:
            if hero_key.startswith('hero') and hero_key != 'hero_base':
                hero_value = self.hero_data[hero_key]

                hero_stats = {
                    'Name': self.localizations['names'].get(hero_key, None),
                }

                hero_stats.update(
                    self._map_attr_names(hero_value['m_mapStartingStats'], maps.get_hero_attr)
                )


                # Parse Tech scaling
                if 'm_mapScalingStats' in hero_value:
                    # Move scaling data under TechScaling key
                    hero_stats["TechScaling"] = {}

                    # Transform each value within m_mapScalingStats from

                    # "MaxMoveSpeed": {
                    #     "eScalingStat": "ETechPower",
                    #     "flScale": 0.04
                    # },

                    # to

                    # "MaxMoveSpeed": 0.04
                    spirit_scalings = hero_value['m_mapScalingStats']
                    for hero_scaling_key, hero_scaling_value in spirit_scalings.items():
                        hero_stats["TechScaling"][maps.get_hero_attr(hero_scaling_key)] = hero_scaling_value["flScale"]

                        # Ensure the only scalar in here is ETechPower
                        if "ETechPower" != hero_scaling_value["eScalingStat"]:
                            raise Exception(f"Expected scaling key 'ETechPower' but is: {hero_scaling_value["eScalingStat"]}")


                weapon_stats = self._parse_hero_weapon(hero_value)
                hero_stats.update(weapon_stats)

                # Parse Level scaling
                if 'm_mapStandardLevelUpUpgrades' in hero_value:
                    level_scalings = hero_value['m_mapStandardLevelUpUpgrades']

                    hero_stats["LevelScaling"] = {}
                    for key in level_scalings:
                        hero_stats["LevelScaling"][maps.get_level_mod(key)] = level_scalings[key]

                all_hero_stats[hero_key] = sort_dict(hero_stats)

        json.write(self.OUTPUT_DIR + 'json/hero-data.json', sort_dict(all_hero_stats))

    def _parse_hero_weapon(self, hero_value):
        weapon_stats = {}

        weapon_prim_id = hero_value['m_mapBoundAbilities']['ESlot_Weapon_Primary']
        weapon_prim = self.abilities_data[weapon_prim_id]['m_WeaponInfo']

        weapon_stats = {
            'BulletDamage': weapon_prim['m_flBulletDamage'],
            'RoundsPerSecond': 1 / weapon_prim['m_flCycleTime'],
            'ClipSize': weapon_prim['m_iClipSize'],
            'ReloadTime': weapon_prim['m_reloadDuration'],
        }

        weapon_stats['Dps'] = weapon_stats['BulletDamage'] * weapon_stats['BulletsPerSec']
        return weapon_stats

    def _parse_abilities(self):
        print('Parsing Abilities...')

        ability_keys = self.abilities_data.keys()
        all_abilities = dict()

        for ability_key in ability_keys:
            ability_data = {}

            ability_data['name'] = self.localizations['names'].get(ability_key, 'Unknown')

            all_abilities[ability_key] = ability_data

        json.write(self.OUTPUT_DIR + 'json/ability-data.json', all_abilities)

    def _parse_items(self):
        print('Parsing Items...')

        all_items = {}

        for key in self.abilities_data:
            ability = self.abilities_data[key]
            if type(ability) is not dict:
                continue

            if 'm_eAbilityType' not in ability:
                continue

            if ability['m_eAbilityType'] != 'EAbilityType_Item':
                continue

            item_value = ability
            item_ability_attrs = item_value['m_mapAbilityProperties']

            # Assign target types
            target_types = None
            if 'm_nAbilityTargetTypes' in item_value:
                target_types = self._format_pipe_sep_string(
                    item_value['m_nAbilityTargetTypes'], maps.get_target_type
                )

            # Assign shop filters
            shop_filters = None
            if 'm_eShopFilters' in item_value:
                shop_filters = self._format_pipe_sep_string(
                    item_value['m_eShopFilters'], maps.get_shop_filter
                )

            tier = maps.get_tier(item_value.get('m_iItemTier'))

            cost = None
            if tier is not None:
                cost = self.generic_data['m_nItemPricePerTier'][int(tier)]

            parsed_item_data = {
                'Name': self.localizations['names'].get(key),
                'Description': '',
                'Cost': str(cost),
                'Tier': tier,
                'Activation': maps.get_ability_activation(item_value['m_eAbilityActivation']),
                'Slot': maps.get_slot_type(item_value.get('m_eItemSlotType')),
                'Components': None,
                # 'ImagePath': str(item_value.get('m_strAbilityImage', None)),
                'TargetTypes': target_types,
                'ShopFilters': shop_filters,
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

            description = self.localizations['descriptions'].get(key + '_desc')
            if description is not None:
                # strip away all html tags for displaying as text
                description = re.sub(r'<span\b[^>]*>|<\/span>', '', description)
                parsed_item_data['Description'] = self._format_description(
                    description, parsed_item_data
                )

            all_items[key] = parsed_item_data

        json.write(self.OUTPUT_DIR + 'json/item-data.json', sort_dict(all_items))

    # format description with data. eg. "When you are above {s:LifeThreshold}% health"
    # should become "When you are above 20% health"
    def _format_description(self, desc, data):
        def replace_match(match):
            key = match.group(1)
            return data.get(key, '')

        formatted_desc = re.sub(r'\{s:(.*?)\}', replace_match, desc)
        return formatted_desc

    # Add items to mermaid tree
    def _add_children_to_tree(self, parent_key, child_keys):
        for child_key in child_keys:
            links.append(Link(Node(self.localizations['names'].get(child_key)), Node(parent_key)))

    # maps all keys in an object using the provided function
    def _map_attr_names(self, data, func):
        output_data = dict()
        for key in data:
            mapped_key = func(key)
            output_data[mapped_key] = data[key]

        return output_data

    # Formats pipe separated string and maps the value
    # eg. "A | B | C" to [map(A), map(B), map(C)]
    def _format_pipe_sep_string(self, pipe_sep_string, map_func):
        output_array = []
        for value in pipe_sep_string.split('|'):
            # strip all whitespace
            value = value.replace(' ', '')
            if value == '':
                continue
            mapped_value = map_func(value)
            output_array.append(mapped_value)

        return output_array


def sort_dict(dict):
    keys = list(dict.keys())
    keys.sort()
    return {key: dict[key] for key in keys}


if __name__ == '__main__':
    parser = Parser()
    parser.run()
