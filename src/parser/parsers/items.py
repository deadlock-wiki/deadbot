import math
from typing import Dict, Any, Optional
from python_mermaid.diagram import MermaidDiagram, Node, Link
import utils.string_utils as string_utils
import utils.num_utils as num_utils
import parser.maps as maps
from parser.maps import get_scale_type
from loguru import logger


class ItemParser:
    def __init__(self, abilities_data, generic_data, localizations):
        self.abilities_data = abilities_data
        self.generic_data = generic_data
        self.localizations = localizations
        self.nodes = []
        self.links = []

    def run(self):
        all_items = {}
        for key in self.abilities_data:
            ability = self.abilities_data[key]
            if type(ability) is not dict:
                continue

            # Skip the base class for cosmetics
            if key == 'cosmetic_base':
                continue

            if 'm_eAbilityType' not in ability:
                continue
            if ability['m_eAbilityType'] not in ['EAbilityType_Item', 'EAbilityType_Cosmetic']:
                continue
            try:
                all_items[key] = self._parse_item(key)
            except Exception as e:
                logger.error(f'Failed to parse item {key}')
                raise e
        chart = MermaidDiagram(title='Items', nodes=self.nodes, links=self.links)
        return (all_items, chart)

    def _parse_item(self, key):
        ability = self.abilities_data[key]
        item_value = ability

        item_ability_attrs = item_value.get('m_mapAbilityProperties', {}).copy()
        elevated_attrs = item_value.get('m_vecElevatedAbilityProperties', {})
        if isinstance(elevated_attrs, dict):
            item_ability_attrs.update(elevated_attrs)

        # Assign target types
        target_types = None
        if 'm_nAbilityTargetTypes' in item_value:
            target_types = self._format_pipe_sep_string(item_value['m_nAbilityTargetTypes'], maps.get_target_type)

        # Assign shop filters
        shop_filters = None
        if 'm_eShopFilters' in item_value:
            shop_filters = self._format_pipe_sep_string(item_value['m_eShopFilters'], maps.get_shop_filter)

        tier = maps.get_tier(item_value.get('m_iItemTier'))
        cost = None
        if tier is not None:
            cost = self.generic_data['m_nItemPricePerTier'][int(tier)]

        # Determine if the item is in Street Brawl.
        requirements = item_value.get('m_eAbilityRequirements', '')
        is_street_brawl = 'ERequirementStreetBrawl' in [r.strip() for r in requirements.split('|')]

        parsed_item_data = {
            'Name': self.localizations.get(key),
            'Description': '',
            'Cost': cost,
            'Tier': int(tier) if tier is not None else None,
            'Activation': maps.get_ability_activation(item_value.get('m_eAbilityActivation')),
            'Slot': maps.get_slot_type(item_value.get('m_eItemSlotType')),
            'Components': None,
            'TargetTypes': target_types,
            'ShopFilters': shop_filters,
            'IsDisabled': self._is_disabled(item_value),
            'StreetBrawl': is_street_brawl,
        }

        # Process attributes and extract scaling information
        for attr_key in item_ability_attrs.keys():
            attr = item_ability_attrs[attr_key]

            scaling_data = self._extract_scaling(attr, key, attr_key)

            include_attr = True
            if attr.get('m_eStatsUsageFlags') == 'ConditionallyApplied':
                include_attr = True
            if attr.get('m_strLocTokenOverride'):
                include_attr = True

            if scaling_data:
                parsed_item_data[attr_key] = scaling_data
            elif 'm_strValue' in attr:
                value = num_utils.assert_number(attr['m_strValue'])
                # Only filter if the value is a number and it is zero
                if num_utils.is_zero(value):
                    continue  # Skip this zero-value attribute
                else:
                    parsed_item_data[attr_key] = value
            elif include_attr:
                parsed_item_data[attr_key] = {}
            else:
                logger.trace(f'Missing m_strValue attr in item {key} attribute {attr_key}')

        if 'm_iMaxLevel' in item_value:
            parsed_item_data['MaxLevel'] = item_value['m_iMaxLevel']

        # Extract progression stats (e.g. for seasonal items like Snowball)
        progression = {}
        for k, v in item_value.items():
            if k.startswith('m_progression'):
                prop_name = k.replace('m_progression', '')
                if isinstance(v, dict) and 'm_mapLevelsToValue' in v:
                    prog_entry = {'Levels': v['m_mapLevelsToValue']}
                    if 'm_eBetweenBehavior' in v:
                        prog_entry['Behavior'] = v['m_eBetweenBehavior']
                    progression[prop_name] = prog_entry

        if progression:
            parsed_item_data['Progression'] = progression

        # ignore description formatting for disabled items
        if not parsed_item_data['IsDisabled']:
            description = self.localizations.get(key + '_desc')
            parsed_item_data['Description'] = string_utils.format_description(
                description,
                parsed_item_data,
                self.localizations,
            )
        else:
            description = self.localizations.get(key + '_desc')
            parsed_item_data['Description'] = description

        # Process item components if they exist
        if 'm_vecComponentItems' in item_value:
            parsed_item_data['Components'] = item_value['m_vecComponentItems']
            parent_name = parsed_item_data['Name']
            if parent_name is None:
                parent_name = key
            self._add_children_to_tree(parent_name, parsed_item_data['Components'])

        property_upgrades = self._parse_property_upgrades(item_value)
        if property_upgrades:
            parsed_item_data['PropertyUpgrades'] = property_upgrades

        tooltip_sections = self._parse_tooltip_sections(item_value)
        if tooltip_sections:
            parsed_item_data['TooltipSections'] = tooltip_sections

        return parsed_item_data

    def _parse_property_upgrades(self, item_value):
        property_upgrades = {}
        vec_ability_upgrades = item_value.get('m_vecAbilityUpgrades', [])
        for ability_upgrade in vec_ability_upgrades:
            vec_property_upgrades = ability_upgrade.get('m_vecPropertyUpgrades', [])
            for prop_upgrade in vec_property_upgrades:
                prop_name = prop_upgrade.get('m_strPropertyName')
                bonus_str = prop_upgrade.get('m_strBonus')

                if not prop_name or bonus_str is None:
                    continue

                bonus_value = num_utils.assert_number(bonus_str)
                property_upgrades[prop_name] = bonus_value

        return property_upgrades

    def _parse_tooltip_sections(self, item_value):
        sections = item_value.get('m_vecTooltipSectionInfo')
        if not isinstance(sections, list):
            return None

        parsed_sections = []

        for section in sections:
            section_type = section.get('m_eAbilitySectionType')
            vec_attrs = section.get('m_vecSectionAttributes', [])

            parsed_entries = []
            for attr in vec_attrs:
                entry = {
                    'LocString': attr.get('m_strLocString'),
                    'ImportantProperties': [],
                    'Properties': [],
                }

                important = attr.get('m_vecImportantAbilityProperties', [])
                for imp in important:
                    prop = imp.get('m_strImportantProperty')
                    if prop:
                        entry['ImportantProperties'].append(prop)

                elevated_props = attr.get('m_vecElevatedAbilityProperties', [])
                props = attr.get('m_vecAbilityProperties', [])

                if isinstance(elevated_props, list):
                    entry['Properties'].extend(elevated_props)
                if isinstance(props, list):
                    entry['Properties'].extend(props)

                parsed_entries.append(entry)

            parsed_sections.append(
                {
                    'Type': section_type,
                    'Entries': parsed_entries,
                }
            )

        return parsed_sections

    def _extract_scaling(self, attr: Dict[str, Any], item_key: str, attr_key: str) -> Optional[Dict[str, Any]]:
        """
        Return nested scaling dict for an attribute (matches hero data schema).
        """
        scale_func = attr.get('m_subclassScaleFunction')
        if not isinstance(scale_func, dict):
            return None

        raw_scale_value = scale_func.get('m_flStatScale')
        if raw_scale_value is None:
            return None

        base_value_str = attr.get('m_strValue')
        if base_value_str is None:
            return None

        scale_type = scale_func.get('m_eSpecificStatScaleType')
        human_type = get_scale_type(scale_type)
        if not human_type:
            return None

        try:
            base_value = num_utils.assert_number(base_value_str)
            scale_value = num_utils.assert_number(raw_scale_value)
            if math.isnan(scale_value) or math.isinf(scale_value):
                return None
        except (ValueError, TypeError):
            return None

        return {'Value': base_value, 'Scale': {'Value': scale_value, 'Type': human_type}}

    def _is_disabled(self, item):
        is_disabled = False
        if 'm_bDisabled' in item:
            flag = item['m_bDisabled']
            # flag is 1 of [True, False, 'true', 'false']
            if flag in [True, 'true']:
                is_disabled = True
            elif flag in [False, 'false']:
                is_disabled = False
            else:
                raise ValueError(f'New unexpected value for m_bDisabled: {flag}')
        return is_disabled

    def _add_children_to_tree(self, parent_key, child_keys):
        """Add items to mermaid tree"""
        for child_key in child_keys:
            self.links.append(Link(Node(self.localizations.get(child_key)), Node(parent_key)))

    def _format_pipe_sep_string(self, pipe_sep_string, map_func):
        """
        Formats pipe separated string and maps the value
        eg. "A | B | C" to [map(A), map(B), map(C)]
        """
        output_array = []
        for value in pipe_sep_string.split('|'):
            # strip all whitespace
            value = value.replace(' ', '')
            if value == '':
                continue
            mapped_value = map_func(value)
            output_array.append(mapped_value)

        return output_array
