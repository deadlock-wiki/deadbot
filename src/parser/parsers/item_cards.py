class ItemCardParser:
    def __init__(self, parsed_items, abilities):
        self.parsed_items = parsed_items
        self.abilities = abilities
        self.used_attributes = []

    def run(self):
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
        self.item_key = key
        self.item = item
        self.used_attributes = ['Name', 'Description']

        card = {
            'Key': key,
            'Name': item.get('Name', key),
            'Cost': item.get('Cost'),
            'Tier': item.get('Tier'),
            'Slot': item.get('Slot'),
            'Activation': item.get('Activation'),
            'Components': item.get('Components'),
            'StreetBrawl': item.get('StreetBrawl'),
        }

        # Tooltip sections → Main/Alt blocks
        tooltip = item.get('TooltipSections')
        if tooltip:
            card.update(self._parse_tooltip_sections(tooltip))

        # Property upgrades
        if 'PropertyUpgrades' in item:
            card['Upgrades'] = item['PropertyUpgrades']

        # Remaining attributes grouped by type
        card.update(self._parse_remaining_attributes())

        return card

    SECTION_TYPE_MAP = {
        'EArea_Innate': 'Innate',
        'EArea_Active': 'Active',
        'EArea_Passive': 'Passive',
    }

    def _parse_tooltip_sections(self, sections):
        ui_sections = {}
        index = 1

        for section in sections:
            raw_type = section.get('Type') or section.get('m_eAbilitySectionType')
            human_type = self.SECTION_TYPE_MAP.get(raw_type, raw_type)

            parsed = {
                'Type': human_type,
                'DescKey': None,
                'Cooldown': None,
                'ChargeUp': None,
                'Main': [],
                'Alt': [],
            }

            # entries may be under 'Entries' or 'm_vecSectionAttributes'
            entries = section.get('Entries') or section.get('m_vecSectionAttributes') or []

            # Try to get DescKey from the first entry or any entry
            for entry in entries:
                parsed['DescKey'] = entry.get('m_strLocString') or entry.get('LocString') or entry.get('m_strLocStringOverride')
                if parsed['DescKey']:
                    break

            for entry in entries:
                # Important properties
                important_props = entry.get('ImportantProperties') or entry.get('m_vecImportantAbilityProperties') or []
                for prop in important_props:
                    if isinstance(prop, dict):
                        key = prop.get('Key') or prop.get('m_strImportantProperty')
                    else:
                        key = prop  # string directly

                    if key in ['AbilityCooldown', 'AbilityChargeUpTime']:
                        if key == 'AbilityCooldown':
                            parsed['Cooldown'] = self.item.get(key)
                        else:
                            parsed['ChargeUp'] = self.item.get(key)
                    elif key:
                        parsed['Main'].append(self._build_prop_object(key))

                # Normal properties
                normal_props = entry.get('Properties') or entry.get('m_vecAbilityProperties') or []
                for key in normal_props:
                    if key in ['AbilityCooldown', 'AbilityChargeUpTime']:
                        if key == 'AbilityCooldown':
                            parsed['Cooldown'] = self.item.get(key)
                        else:
                            parsed['ChargeUp'] = self.item.get(key)
                    else:
                        parsed['Alt'].append(self._build_prop_object(key))

            ui_sections[f'Info{index}'] = parsed
            index += 1

        return ui_sections

    def _build_prop_object(self, prop_key):
        if prop_key not in self.item:
            return {'Key': prop_key, 'Missing': True}

        value = self.item[prop_key]
        raw_attr = self._get_raw_item_attr(prop_key)

        obj = {
            'Key': prop_key,
        }

        if isinstance(value, dict):
            obj.update(value)
        else:
            obj['Value'] = value

        if raw_attr:
            css = raw_attr.get('m_strCSSClass')
            if css:
                obj['CSSClass'] = css

            usage = raw_attr.get('m_eStatsUsageFlags')
            if usage:
                obj['UsageFlags'] = usage

            override = raw_attr.get('m_strLocTokenOverride')
            if override:
                obj['LocTokenOverride'] = override

        self.used_attributes.append(prop_key)
        return obj

    def _parse_remaining_attributes(self):
        """
        Group leftover attributes into UI categories.
        """
        categories = {
            'Stats': {},
            'Effects': {},
            'Scaling': {},
            'Other': {},
        }

        for prop, value in self.item.items():
            if prop in self.used_attributes:
                continue
            if prop in ['Cost', 'Tier', 'Slot', 'Activation', 'Components', 'StreetBrawl']:
                continue

            raw_attr = self._get_raw_item_attr(prop)
            if raw_attr is None:
                continue

            entry = {'Name': prop}

            if isinstance(value, dict):
                entry.update(value)
            else:
                entry['Value'] = value

            css = raw_attr.get('CSSClass')
            if css:
                entry['Type'] = css

            # Categorization rules
            if 'Scale' in entry:
                categories['Scaling'][prop] = entry
            elif css in ['damage', 'tech_damage', 'bullet_damage']:
                categories['Effects'][prop] = entry
            elif css in ['health', 'healing', 'armor']:
                categories['Stats'][prop] = entry
            else:
                categories['Other'][prop] = entry

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _get_raw_item_attr(self, attr_key):
        """
        Look up raw ability data for the item.
        """
        raw = self.abilities.get(self.item_key)
        if not raw:
            return None

        props = raw.get('m_mapAbilityProperties', {})
        elevated = raw.get('m_vecElevatedAbilityProperties', {})

        merged = {}
        merged.update(props)
        if isinstance(elevated, dict):
            merged.update(elevated)

        return merged.get(attr_key)
