from python_mermaid.diagram import MermaidDiagram, Node, Link
import utils.string_utils as string_utils
import parser.maps as maps
from loguru import logger

class ItemParser:
    nodes = []
    links = []
    
    # Define scaling types that we want to extract
    # This makes it easy to add new scaling types in the future
    SCALING_TYPES = {
        'ETechPower': 'Spirit Scaling',
        'ELevelUpBoons': 'Boon Scaling'
    }
    
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
            'TargetTypes': target_types,
            'ShopFilters': shop_filters,
            'IsDisabled': self._is_disabled(item_value),
        }
        
        # Process attributes and extract scaling information
        for attr_key in item_ability_attrs.keys():
            attr = item_ability_attrs[attr_key]
            
            if 'm_strValue' in attr:
                # Keep the original string value for backward compatibility
                parsed_item_data[attr_key] = attr['m_strValue']
                
                # Check for scaling information
                scaling_info = self._extract_scaling_info(attr, key, attr_key)
                if scaling_info:
                    scaling_type, scaling_value = scaling_info
                    # Create a new key with _scaling suffix
                    scaled_key = f"{attr_key}_scaling"
                    parsed_item_data[scaled_key] = {scaling_type: scaling_value}
            else:
                logger.warning(f'Missing m_strValue attr in item {key} attribute {attr_key}')

        # ignore description formatting for disabled items
        if not parsed_item_data['IsDisabled']:
            description = self.localizations.get(key + '_desc')
            parsed_item_data['Description'] = string_utils.format_description(
                description, parsed_item_data, self.localizations
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

        return parsed_item_data
    
    def _extract_scaling_info(self, attr, item_key, attr_key):
        """
        Extract scaling information from an attribute if it exists.
        Returns a tuple of (scaling_type, scaling_value) or None if no scaling is found.
        
        Args:
            attr: The attribute dictionary to check for scaling info
            item_key: The key of the item being parsed (for logging)
            attr_key: The key of the attribute being parsed (for logging)
        """
        if 'm_subclassScaleFunction' in attr:
            scale_func = attr['m_subclassScaleFunction']
            if 'm_eSpecificStatScaleType' in scale_func:
                stat_scale_type = scale_func['m_eSpecificStatScaleType']
                # Check if this is a scaling type we're interested in
                if stat_scale_type in self.SCALING_TYPES:
                    scaling_type = self.SCALING_TYPES[stat_scale_type]
                    raw_scaling_value = scale_func.get('m_flStatScale')
                    if raw_scaling_value is not None:
                        # Safely convert to float with error handling
                        try:
                            scaling_value = float(raw_scaling_value)
                            return (scaling_type, scaling_value)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid scaling value: {raw_scaling_value} " 
                                f"in {item_key}.{attr_key}"
                            )
        return None
    
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
