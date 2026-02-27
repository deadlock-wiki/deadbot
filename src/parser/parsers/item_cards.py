from parser.maps import get_section_type


class ItemCardParser:
    def __init__(self, parsed_items, abilities):
        self.parsed_items = parsed_items
        self.abilities = abilities
        self.used_attributes = []

    def run(self):
        """Parse all items in parsed_items."""
        output = {}
        for key, item in self.parsed_items.items():
            try:
                parsed = self._parse_item_card(key, item)
                if parsed:
                    output[key] = parsed
            except Exception as e:
                raise Exception(f'Failed to parse item card for {key}: {e}')
        return output

    def _parse_item_card(self, key, item):
        """Parse a single item card."""
        self.item_key = key
        self.item = item
        self.used_attributes = [
            'Name',
            'Description',
            'Cost',
            'Tier',
            'Slot',
            'Activation',
            'Components',
            'TargetTypes',
            'ShopFilters',
            'IsDisabled',
            'StreetBrawl',
            'PropertyUpgrades',
        ]

        card = {
            'Key': key,
            'Name': item.get('Name', key),
            'Description': item.get('Description', ''),
            'Cost': item.get('Cost'),
            'Tier': item.get('Tier'),
            'Slot': item.get('Slot'),
            'Activation': item.get('Activation'),
            'Components': item.get('Components'),
            'TargetTypes': item.get('TargetTypes'),
            'ShopFilters': item.get('ShopFilters'),
            'IsDisabled': item.get('IsDisabled'),
            'StreetBrawl': item.get('StreetBrawl'),
        }

        # Parse tooltip sections if available
        raw_ability = self.abilities.get(key)
        tooltip_sections = raw_ability.get('m_vecTooltipSectionInfo') if raw_ability else None
        if tooltip_sections:
            card.update(self._parse_tooltip_sections(tooltip_sections))

        # Include property upgrades
        if 'PropertyUpgrades' in item:
            card['Upgrades'] = item['PropertyUpgrades']

        # Parse remaining attributes inline
        card.update(self._parse_remaining_attributes())

        # Promote AbilityCooldown from Other into the last non-Innate Info
        if 'Other' in card and 'AbilityCooldown' in card['Other']:
            ability_cd = card['Other']['AbilityCooldown']
            info_keys = [k for k in card.keys() if k.startswith('Info')]
            non_innate_infos = [card[k] for k in info_keys if card[k].get('Type') != 'Innate']
            if non_innate_infos:
                last_info = non_innate_infos[-1]
                # Only set if Cooldown or ChargeUp is missing
                if last_info.get('Cooldown') is None and last_info.get('ChargeUp') is None:
                    last_info['Cooldown'] = ability_cd.get('Value')
                    # Remove from Other
                    del card['Other']['AbilityCooldown']
                    if not card['Other']:
                        del card['Other']

        return card

    def _parse_tooltip_sections(self, sections):
        """Parse Info sections into Main/Alt blocks."""
        ui_sections = {}
        index = 1

        for section in sections:
            raw_type = section.get('Type') or section.get('m_eAbilitySectionType')
            human_type = get_section_type(raw_type)

            parsed = {
                'Type': human_type,
                'DescKey': None,
                'Cooldown': None,
                'ChargeUp': None,
                'Main': [],
                'Alt': [],
            }

            entries = section.get('Entries') or section.get('m_vecSectionAttributes') or []

            for entry in entries:
                if not parsed['DescKey']:
                    parsed['DescKey'] = entry.get('m_strLocString') or entry.get('LocString') or entry.get('m_strLocStringOverride')

                elevated_props = entry.get('m_vecElevatedAbilityProperties') or []
                for key in elevated_props:
                    prop_obj = self._build_prop_object(key)
                    if prop_obj:
                        parsed['Main'].append(prop_obj)
                        self.used_attributes.append(key)

            for entry in entries:
                # Process important properties
                important_props = entry.get('ImportantProperties') or entry.get('m_vecImportantAbilityProperties') or []
                for prop in important_props:
                    if isinstance(prop, dict):
                        key = prop.get('Key') or prop.get('m_strImportantProperty')
                    else:
                        key = prop
                    if key in ['AbilityCooldown', 'AbilityChargeUpTime']:
                        if key == 'AbilityCooldown':
                            parsed['Cooldown'] = self.item.get(key)
                            self.used_attributes.append(key)
                        else:
                            parsed['ChargeUp'] = self.item.get(key)
                            self.used_attributes.append(key)
                    elif key:
                        prop_obj = self._build_prop_object(key)
                        if prop_obj:
                            parsed['Main'].append(prop_obj)

                # Process normal properties
                normal_props = entry.get('Properties') or entry.get('m_vecAbilityProperties') or []
                for key in normal_props:
                    if key in ['AbilityCooldown', 'AbilityChargeUpTime']:
                        if key == 'AbilityCooldown':
                            parsed['Cooldown'] = self.item.get(key)
                            self.used_attributes.append(key)
                        else:
                            parsed['ChargeUp'] = self.item.get(key)
                            self.used_attributes.append(key)
                    else:
                        prop_obj = self._build_prop_object(key)
                        if prop_obj:
                            parsed['Alt'].append(prop_obj)
                            self.used_attributes.append(key)

            ui_sections[f'Info{index}'] = parsed
            index += 1

        return ui_sections

    def _build_prop_object(self, prop_key):
        """Build a property object for an item attribute, including scale if available."""
        if prop_key not in self.item:
            return None  # safely skip missing attributes

        value = self.item[prop_key]
        raw_attr = self._get_raw_item_attr(prop_key)

        # start with Key at the top
        obj = {'Key': prop_key}

        # Base value
        if isinstance(value, dict):
            obj.update(value)
        else:
            obj['Value'] = value

        # Safe scaling handling
        if raw_attr:
            scale_func = raw_attr.get('m_subclassScaleFunction')
            if isinstance(scale_func, dict):
                raw_scale_value = scale_func.get('m_flStatScale')
                base_value_str = raw_attr.get('m_strValue') or value
                scale_type = scale_func.get('m_eSpecificStatScaleType')
                if raw_scale_value is not None and scale_type:
                    try:
                        from parser.maps import get_scale_type

                        try:
                            human_type = get_scale_type(scale_type)
                        except Exception:
                            human_type = None  # unknown scale type is safely ignored

                        if human_type:
                            scale_value = float(raw_scale_value)
                            base_value = float(base_value_str)
                            obj['Value'] = base_value
                            obj['Scale'] = {'Value': scale_value, 'Type': human_type}
                    except (ValueError, TypeError):
                        pass

            # CSS class and other attributes
            type = raw_attr.get('m_strCSSClass') or raw_attr.get('CSSClass')
            if type:
                obj['Type'] = type

            usage = raw_attr.get('m_eStatsUsageFlags')
            if usage:
                obj['UsageFlags'] = usage

            override = raw_attr.get('m_strLocTokenOverride')
            if override:
                obj['LocTokenOverride'] = override

        self.used_attributes.append(prop_key)
        return obj

    def _parse_remaining_attributes(self):
        """Process leftover item attributes into a single 'Other' category."""
        other = {}

        for prop, value in self.item.items():
            if prop in self.used_attributes:
                continue

            entry = self._build_prop_object(prop)
            if entry is None:
                continue

            other[prop] = entry

        return {'Other': other} if other else {}

    def _get_raw_item_attr(self, attr_key):
        """Return the raw ability attribute data for a given item key."""
        raw = self.abilities.get(self.item_key)
        if not raw:
            return None

        merged = {}
        props = raw.get('m_mapAbilityProperties', {})
        if isinstance(props, dict):
            merged.update(props)

        elevated = raw.get('m_vecElevatedAbilityProperties', {})
        if isinstance(elevated, dict):
            merged.update(elevated)
        elif isinstance(elevated, list):
            for entry in elevated:
                if isinstance(entry, dict) and 'm_strPropertyName' in entry:
                    merged[entry['m_strPropertyName']] = entry
                elif isinstance(entry, str):
                    merged[entry] = entry

        return merged.get(attr_key)
