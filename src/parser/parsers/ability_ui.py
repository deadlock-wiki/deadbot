class AbilityUiParser:
    def __init__(self, abilities, parsed_heroes, localizations):
        self.abilities = abilities
        self.parsed_heroes = parsed_heroes
        self.localizations = localizations

    def run(self):
        output = {}
        for hero_key, hero in self.parsed_heroes.items():
            for index, ability in hero['BoundAbilities'].items():
                # skip "generic_person"
                ability_key = ability['Key']
                if ability_key.startswith('genericperson'):
                    continue

                try:
                    parsed_ui = self._parse_ability_ui(ability)
                    if parsed_ui is not None:
                        output[hero_key] = parsed_ui
                except Exception as e:
                    print(f'[ERROR] Failed to parse ui for ability {ability_key}', e)
                    continue

        return output

    def _parse_ability_ui(self, parsed_ability):
        parsed_ui = {}
        raw_ability = self.abilities[parsed_ability['Key']]

        # Some heroes do not have ui information, so are likely unplayable or in development
        # TODO - a check for if hero is in development to make sure
        if 'm_AbilityTooltipDetails' not in raw_ability:
            return None

        info_sections = raw_ability['m_AbilityTooltipDetails']['m_vecAbilityInfoSections']
        # if len(info_sections) > 2:
        #     raise Exception(f'Found {len(info_sections)} sections, but only 2 are supported')

        for index, info_section in enumerate(info_sections):
            # Each info section consists of some combination of
            # title, description, main properties, and alternate properties
            parsed_info_section = {
                'Title': None,
                'Description': None,
                'Main': [],
                'Alt': [],
            }

            title_key = info_section.get('m_strPropertiesTitleLocString')
            if title_key is not None:
                # localization keys are prefixed with a "#"
                parsed_info_section['Title'] = self.localizations[title_key.replace('#', '')]

            desc_key = info_section.get('m_strLocString')
            if desc_key is not None:
                # localization keys are prefixed with a "#"
                parsed_info_section['Description'] = self.localizations[desc_key.replace('#', '')]

            # skip any UI that requires an upgraded ability to display it
            if 'm_strAbilityPropertyUpgradeRequired' in info_section:
                continue

            # some blocks might just be a description
            if 'm_vecAbilityPropertiesBlock' not in info_section:
                continue

            ability_prop_block = info_section['m_vecAbilityPropertiesBlock']
            if len(ability_prop_block) > 1:
                raise Exception(
                    f'Expected only one ability property block, but found {len(ability_prop_block)}'
                )

            main_props = ability_prop_block[0]['m_vecAbilityProperties']

            for prop in main_props:
                attr_key = None
                prop_requires_upgrade = False

                for prop_attr, prop_value in prop.items():
                    match prop_attr:
                        case 'm_strStatusEffectValue':
                            attr_key = prop_value

                        case 'm_strImportantProperty':
                            # This is only used in case m_strStatusEffectValue is not found
                            if attr_key is None:
                                attr_key = prop_value

                        case 'm_bRequiresAbilityUpgrade':
                            prop_requires_upgrade = True

                        case 'm_bShowPropertyValue':
                            # this has no use at the moment, as we want to always show the prop value
                            continue

                        case _:
                            print('[ERROR] Unhandled property', prop_attr)

                # skip property that requires ability to be upgraded
                if prop_requires_upgrade:
                    continue

                if attr_key is None:
                    raise Exception(f"Missing value for ability {parsed_ability['Name']}")

                if attr_key not in parsed_ability:
                    print(
                        f'[WARN] - {attr_key} is probably an upgrade attr that is not tagged as such'
                    )
                    continue

                parsed_info_section['Main'].append({prop_value: parsed_ability[attr_key]})

                # if attr not in parsed_ability:
                #     print(f'Missing base stat {attr}')
                #     continue
            # print(info_section)
            # side_props = info_section['m_vecBasicProperties']

            parsed_ui[f'Info{index+1}'] = parsed_info_section

        # remaining properties are placed into "Other"
        return parsed_ui
