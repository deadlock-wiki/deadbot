import sys
import os
from .item_objects import Item
from python_mermaid.diagram import MermaidDiagram, Node, Link

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import utils.string_utils as string_utils
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
                'Name': self.localizations.get(key),
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

            description = self.localizations.get(key + '_desc')
            parsed_item_data['Description'] = string_utils.format_description(
                description, parsed_item_data, maps.KEYBIND_MAP
            )

            if 'm_vecComponentItems' in item_value:
                parsed_item_data['Components'] = item_value['m_vecComponentItems']
                parent_name = parsed_item_data['Name']
                if (
                    parent_name is None
                ):  # upgrade_headhunter doesnt yet (as of writing) have a localized name, making it
                    # otherwise not appear in item-component-tree.txt
                    parent_name = key
                self._add_children_to_tree(parent_name, parsed_item_data['Components'])

            if 'm_bDisabled' in item_value:
                flag = item_value['m_bDisabled']
                # flag is 1 of [True, False, 'true', 'false']
                if flag in [True, 'true']:
                    is_disabled = True
                elif flag in [False, 'false']:
                    is_disabled = False
                else:
                    raise ValueError(f'New unexpected value for m_bDisabled: {flag}')
            else:
                is_disabled = False
            parsed_item_data['Disabled'] = is_disabled

            all_items[key] = parsed_item_data

        chart = MermaidDiagram(title='Items', nodes=self.nodes, links=self.links)

        # Create Item objects
        Item.hashToObjs(all_items)
        Item.saveObjects()

        Item.loadObjects()
        print(Item.objects['armor_upgrade_t4'].Cost)

        return (all_items, chart)

    # Add items to mermaid tree
    def _add_children_to_tree(self, parent_key, child_keys):
        for child_key in child_keys:
            self.links.append(Link(Node(self.localizations.get(child_key)), Node(parent_key)))

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


def is_enabled(item):
    return not item.get('Disabled', False)
