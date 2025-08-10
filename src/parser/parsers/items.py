from python_mermaid.diagram import MermaidDiagram, Node, Link
import utils.string_utils as string_utils
import parser.maps as maps
from loguru import logger
import math
from typing import Dict, Any, Optional, Tuple, List


class ItemParser:
    """Parses item data from game files, including base stats and scaling (Spirit/Boon)."""

    DEFAULT_SCALING_TYPE_MAP = {
        "ETechPower": "Spirit",               # Spirit scaling 
        "ELevelUpBoons": "Boon",              # Boon scaling 
        # Add new mappings here as needed; can be overridden via constructor
    }

    def __init__(
        self,
        abilities_ Dict[str, Any],
        generic_ Dict[str, Any],
        localizations: Dict[str, str],
        scaling_type_map: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the parser.

        :param abilities_ Raw game ability data (from abilities.vdata)
        :param generic_ Shared constants (e.g., prices per tier)
        :param localizations: String translations by key
        :param scaling_type_map: Optional override for scaling type mapping (e.g., ETechPower → Spirit)
        """
        self.abilities_data = abilities_data
        self.generic_data = generic_data
        self.localizations = localizations
        self.scaling_type_map = scaling_type_map or self.DEFAULT_SCALING_TYPE_MAP

        # Fix shared mutable state
        self.nodes: List[Node] = []
        self.links: List[Link] = []

    def run(self) -> Tuple[Dict[str, Any], MermaidDiagram]:
        """
        Parse all items and generate a Mermaid diagram of component trees.

        :return: Tuple of (parsed_items_dict, mermaid_diagram)
        """
        all_items = {}

        for key in self.abilities_data:
            ability = self.abilities_data[key]
            if not isinstance(ability, dict):
                continue

            ability_type = ability.get('m_eAbilityType')
            if not ability_type or ability_type != 'EAbilityType_Item':
                continue

            try:
                all_items[key] = self._parse_item(key)
            except Exception as e:
                logger.error(f'Failed to parse item {key}')
                raise e

        chart = MermaidDiagram(title='Items', nodes=self.nodes, links=self.links)
        return all_items, chart

    def _parse_item(self, key: str) -> Dict[str, Any]:
        """
        Parse a single item's data into structured format.

        :param key: Item key in abilities_data
        :return: Dictionary of parsed item properties
        """
        ability = self.abilities_data[key]
        item_value = ability
        item_ability_attrs = item_value.get('m_mapAbilityProperties', {})

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
            try:
                cost = str(self.generic_data['m_nItemPricePerTier'][int(tier)])
            except (KeyError, IndexError, ValueError) as e:
                logger.warning(f"Could not resolve cost for tier {tier} on item {key}: {e}")

        parsed_item_data = {
            'Name': self.localizations.get(key),
            'Description': '',
            'Cost': cost,
            'Tier': tier,
            'Activation': maps.get_ability_activation(item_value.get('m_eAbilityActivation', '')),
            'Slot': maps.get_slot_type(item_value.get('m_eItemSlotType')),
            'Components': None,
            'TargetTypes': target_types,
            'ShopFilters': shop_filters,
            'IsDisabled': self._is_disabled(item_value),
            'Scaling': {},  # Will be populated with Spirit, Boon, etc.
        }

        # Process each ability property (e.g. Damage, BonusHealth)
        for attr_key, attr in item_ability_attrs.items():
            # Set base value if available
            if 'm_strValue' in attr:
                parsed_item_data[attr_key] = attr['m_strValue']
            else:
                logger.warning(f'Missing m_strValue in item {key}, attribute {attr_key}')

            # Extract scaling info (Spirit, Boon, etc.) only if m_flStatScale is present
            scaling_entry = self._extract_scaling(attr_key, attr)
            if scaling_entry:
                category, property_name, scale_value = scaling_entry
                if category not in parsed_item_data['Scaling']:
                    parsed_item_data['Scaling'][category] = {}
                parsed_item_data['Scaling'][category][property_name] = scale_value

        # Handle description
        desc_key = key + '_desc'
        description = self.localizations.get(desc_key, '')
        if not parsed_item_data['IsDisabled'] and description:
            parsed_item_data['Description'] = string_utils.format_description(
                description, parsed_item_data, self.localizations
            )
        else:
            parsed_item_data['Description'] = description

        # Handle components and tree
        if 'm_vecComponentItems' in item_value:
            components = item_value['m_vecComponentItems']
            if isinstance(components, list):
                parsed_item_data['Components'] = components
                parent_name = parsed_item_data['Name'] or key
                self._add_children_to_tree(parent_name, components)
            else:
                logger.warning(f"m_vecComponentItems for {key} is not a list: {type(components)}")

        return parsed_item_data

    def _extract_scaling(self, attr_key: str, attr: Dict[str, Any]) -> Optional[Tuple[str, str, float]]:
        """
        Extract scaling data from an ability property ONLY if m_flStatScale is explicitly defined.

        :param attr_key: Name of the property (e.g., 'BonusHealth')
        :param attr: The property dict
        :return: (category, property_name, scale_value) or None if no valid scaling
        """
        scale_func = attr.get('m_subclassScaleFunction')
        if not scale_func:
            return None

        # Skip if scale_func is a list (observed edge case in some dumps)
        if isinstance(scale_func, list):
            logger.debug(f"Skipping list-type m_subclassScaleFunction in {attr_key}")
            return None

        if not isinstance(scale_func, dict):
            return None

        stat_scale_type = scale_func.get('m_eSpecificStatScaleType')
        raw_value = scale_func.get('m_flStatScale')  # Must be present

        # ✅ Only proceed if m_flStatScale exists (its presence indicates actual scaling)
        if not stat_scale_type or raw_value is None:
            return None

        category = self.scaling_type_map.get(stat_scale_type)
        if not category:
            return None  # Unknown scaling type

        # Validate and sanitize numeric input
        if not isinstance(raw_value, (int, float, str)):
            logger.debug(f"Invalid type for m_flStatScale in {attr_key}: {type(raw_value)}")
            return None

        # Coerce and validate string
        if isinstance(raw_value, str):
            raw_value = raw_value.strip()
            if raw_value == "":
                return None

        # Convert to float with safety checks
        try:
            value = float(raw_value)
            if math.isnan(value) or math.isinf(value):
                logger.warning(f"Invalid numeric value (NaN/Inf) for {attr_key}.scale: {raw_value}")
                return None
        except (ValueError, TypeError):
            logger.warning(f"Non-numeric m_flStatScale value for {attr_key}: {raw_value}")
            return None

        return category, attr_key, value

    def _is_disabled(self, item: Dict[str, Any]) -> bool:
        """
        Determine if an item is disabled based on m_bDisabled flag.

        :param item: Item data dict
        :return: True if disabled
        """
        flag = item.get('m_bDisabled')
        if flag is None:
            return False
        if isinstance(flag, bool):
            return flag
        if isinstance(flag, str):
            flag = flag.lower()
            if flag == 'true':
                return True
            if flag == 'false':
                return False
            raise ValueError(f"Unexpected string value for m_bDisabled: {flag}")
        raise ValueError(f"Unexpected type for m_bDisabled: {type(flag)}")

    def _add_children_to_tree(self, parent_key: str, child_keys: List[str]) -> None:
        """
        Add links between child items and parent for Mermaid diagram.

        :param parent_key: Localized or fallback name of parent
        :param child_keys: List of child item keys
        """
        for child_key in child_keys:
            child_name = self.localizations.get(child_key, child_key)
            self.links.append(Link(Node(child_name), Node(parent_key)))

    def _format_pipe_sep_string(self, pipe_sep_string: str, map_func) -> List[Any]:
        """
        Split pipe-separated string, strip whitespace, and map values.

        Example: "A | B | C" → [map(A), map(B), map(C)]

        :param pipe_sep_string: Input string like "Filter1 | Filter2"
        :param map_func: Function to apply to each value
        :return: List of mapped values
        """
        output_array = []
        for value in pipe_sep_string.split('|'):
            value = value.strip()
            if not value:
                continue
            try:
                mapped_value = map_func(value)
                output_array.append(mapped_value)
            except Exception as e:
                logger.warning(f"Failed to map value '{value}' using {map_func.__name__}: {e}")
        return output_array
