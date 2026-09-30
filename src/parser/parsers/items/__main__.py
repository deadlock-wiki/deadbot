import math
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, TypeVar
from parser.parsers.items.components import ItemComponentTree
from parser.parsers.items.progression import extract_progression
from parser.parsers.items.upgrades import parse_property_upgrades
import utils.string_utils as string_utils
import utils.num_utils as num_utils
import parser.maps as maps
from parser.maps import get_scale_type
from loguru import logger


class ScalingValue(TypedDict):
    Value: int | float


class ScalingData(TypedDict):
    Value: int | float
    Scale: ScalingValue


class ParsedItemData(TypedDict, total=False):
    Name: Optional[str]
    Description: Optional[str]
    Cost: Optional[int]
    Tier: Optional[int]
    Activation: object
    Slot: object
    Components: object
    TargetTypes: Optional[List[object]]
    ShopFilters: Optional[List[object]]
    IsDisabled: bool
    StreetBrawl: bool
    IsImbue: bool
    MaxLevel: object
    Progression: object
    PropertyUpgrades: object


MappedValue = TypeVar('MappedValue')


class ItemParser:
    def __init__(
        self,
        abilities_data: Dict[str, object],
        generic_data: Dict[str, object],
        localizations: Dict[str, str],
    ) -> None:
        self.abilities_data = abilities_data
        self.generic_data = generic_data
        self.localizations = localizations
        self.item_component_tree = ItemComponentTree(localizations)

    def run(self) -> Tuple[Dict[str, ParsedItemData], object]:
        all_items: Dict[str, ParsedItemData] = {}
        for key in self.abilities_data:
            ability = self.abilities_data[key]
            if not isinstance(ability, dict):
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

        return (all_items, self.item_component_tree.get_chart())

    def _parse_item(self, key: str) -> ParsedItemData:
        ability = self.abilities_data[key]
        item_value = ability
        item_ability_attrs = item_value.get('m_mapAbilityProperties', {})

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

        parsed_item_data: ParsedItemData = {
            'Name': self.localizations.get(key),
            'Description': None,
            'Cost': cost,
            'Tier': int(tier) if tier is not None else None,
            'Activation': maps.get_ability_activation(item_value.get('m_eAbilityActivation')),
            'Slot': maps.get_slot_type(item_value.get('m_eItemSlotType')),
            'Components': None,
            'TargetTypes': target_types,
            'ShopFilters': shop_filters,
            'IsDisabled': self._is_disabled(item_value),
            'StreetBrawl': is_street_brawl,
            'IsImbue': self._is_imbue(item_value),
        }

        # Process attributes and extract scaling information
        for attr_key in item_ability_attrs.keys():
            attr = item_ability_attrs[attr_key]

            scaling_data = self._extract_scaling(attr)

            if scaling_data:
                parsed_item_data[attr_key] = scaling_data
            elif 'm_strValue' in attr:
                value = num_utils.assert_number(attr['m_strValue'])
                # Only filter if the value is a number and it is zero
                if num_utils.is_zero(value):
                    continue  # Skip this zero-value attribute
                parsed_item_data[attr_key] = value
            else:
                logger.trace(f'Missing m_strValue attr in item {key} attribute {attr_key}')

        if 'm_iMaxLevel' in item_value:
            parsed_item_data['MaxLevel'] = item_value['m_iMaxLevel']

        progression = extract_progression(item_value)
        if progression:
            parsed_item_data['Progression'] = progression

        description = self._extract_description(key, parsed_item_data)
        if description:
            parsed_item_data['Description'] = description

        # Process item components if they exist
        if 'm_vecComponentItems' in item_value:
            components = item_value['m_vecComponentItems']
            parsed_item_data['Components'] = components
            self.item_component_tree.add_component(parsed_item_data['Name'] or key, components)

        property_upgrades = parse_property_upgrades(item_value)
        if property_upgrades:
            parsed_item_data['PropertyUpgrades'] = property_upgrades

        return parsed_item_data

    def _extract_description(self, key: str, parsed_item_data: Dict[str, Any]) -> Optional[str]:
        # ignore description formatting for disabled items
        if not parsed_item_data['IsDisabled']:
            description = self.localizations.get(key + '_desc')
            return string_utils.format_description(
                description,
                parsed_item_data,
                self.localizations,
            )
        else:
            return self.localizations.get(key + '_desc')

    def _extract_scaling(self, attr: Dict[str, object]) -> Optional[ScalingData]:
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

        scale_type = maps.get_specific_scale_type(scale_func)
        if scale_type:
            human_type = get_scale_type(scale_type)
            # a named scale type that the wiki has no mapping for is dropped rather than guessed at
            if human_type is None:
                return None
        else:
            # Fallback to inferring from _class
            human_type = maps.class_to_scale_type(scale_func.get('_class', ''))
            if not human_type:
                human_type = maps.get_scale_type('ETechPower')

        try:
            base_value = num_utils.assert_number(base_value_str)
            scale_value = num_utils.assert_number(raw_scale_value)
            if math.isnan(scale_value) or math.isinf(scale_value) or scale_value == 0:
                return None
        except (ValueError, TypeError):
            return None

        return {
            'Value': base_value,
            'Scale': {'Value': scale_value, 'Type': human_type},
        }

    def _is_disabled(self, item: Dict[str, Any]) -> bool:
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

    def _is_imbue(self, item_value: Dict[str, Any]) -> bool:
        effects = item_value.get('m_TargetAbilityEffectsToApply')

        if not effects:
            return False

        parsed_effects = self._format_pipe_sep_string(effects, lambda x: x)

        return any(effect in maps.get_imbue_tags() for effect in parsed_effects)

    def _format_pipe_sep_string(self, pipe_sep_string: str, map_func: Callable[[str], MappedValue]) -> List[MappedValue]:
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
