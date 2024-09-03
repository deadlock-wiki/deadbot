import sys
import os
import re
from python_mermaid.diagram import MermaidDiagram, Node, Link

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import utils.json_utils as json_utils
from constants import OUTPUT_DIR
import maps


class ItemParser:
    nodes = []
    links = []

    def __init__(self, abilities_data, generic_data, localizations):
        self.abilities_data = abilities_data
        self.generic_data = generic_data
        self.localizations = localizations

    def run(self):
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

        json_utils.write(OUTPUT_DIR + 'json/item-data.json', json_utils.sort_dict(all_items))

        chart = MermaidDiagram(title='Items', nodes=self.nodes, links=self.links)

        with open(OUTPUT_DIR + '/item-component-tree.txt', 'w') as f:
            f.write(str(chart))

    # Add items to mermaid tree
    def _add_children_to_tree(self, parent_key, child_keys):
        for child_key in child_keys:
            self.links.append(
                Link(Node(self.localizations['names'].get(child_key)), Node(parent_key))
            )

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

    # format description with data. eg. "When you are above {s:LifeThreshold}% health"
    # should become "When you are above 20% health"
    def _format_description(self, desc, data):
        def replace_match(match):
            key = match.group(1)
            return data.get(key, '')

        formatted_desc = re.sub(r'\{s:(.*?)\}', replace_match, desc)
        return formatted_desc
