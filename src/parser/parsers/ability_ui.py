import sys
import os

# bring parent modules in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.string_utils as string_utils


class AbilityUiParser:
    def __init__(self, abilities, parsed_heroes, localizations):
        self.abilities = abilities
        self.parsed_heroes = parsed_heroes
        self.localizations = localizations

    def run(self):
        output = {}
        for hero_key, hero in self.parsed_heroes.items():
            hero_abilities = {}
            for index, ability in hero['BoundAbilities'].items():
                # skip "generic_person"
                ability_key = ability['Key']
                if ability_key.startswith('genericperson'):
                    continue

                try:
                    parsed_ui = self._parse_ability_ui(hero_key, ability)
                    if parsed_ui is not None:
                        hero_abilities[index] = parsed_ui
                except Exception as e:
                    print(f'[ERROR] Failed to parse ui for ability {ability_key}', e)
                    continue

            output[hero_key] = hero_abilities

        return output

    def _parse_ability_ui(self, hero_key, parsed_ability):
        parsed_ui = {
            'Name': self.localizations[parsed_ability['Key']],
        }

        description = (self.localizations.get(parsed_ability['Key'] + '_desc'),)

        # required variables to insert into the description
        format_vars = (parsed_ability, maps.KEYBIND_MAP, {'hero_name': self.localizations[hero_key]})
        parsed_ui['Description'] = string_utils.format_description(description, *format_vars)

        raw_ability = self.abilities[parsed_ability['Key']]

        # Some heroes do not have ui information, so are likely unplayable or in development
        # TODO - a check for if hero is in development to make sure
        if 'm_AbilityTooltipDetails' not in raw_ability:
            return None

        info_sections = raw_ability['m_AbilityTooltipDetails']['m_vecAbilityInfoSections']
        # if len(info_sections) > 2:
        #     raise Exception(f'Found {len(info_sections)} sections, but only 2 are supported')

        handled_keys = [
            'm_strAbilityPropertyUpgradeRequired',
            'm_vecAbilityPropertiesBlock',
            'm_strLocString',
            'm_vecBasicProperties',
        ]
        for index, info_section in enumerate(info_sections):
            # skip any UI that requires an upgraded ability to display it
            if 'm_strAbilityPropertyUpgradeRequired' in info_section:
                continue

            for key in info_section:
                if key not in handled_keys:
                    raise Exception(f'Unhandled key in info section {key}')

            # Each info section consists of some combination of
            # title, description, main properties, and alternate properties
            parsed_info_section = {
                'Main': [],
                'Alt': [],
            }

            desc_key = info_section.get('m_strLocString')
            if desc_key is not None:
                # localization keys are prefixed with a "#"
                desc_key = desc_key.replace('#', '')
                if desc_key not in self.localizations:
                    raise Exception(f'Missing description for key {desc_key}')

                description = self.localizations[desc_key]
                # required variables to insert into the description
                format_vars = (
                    parsed_ability,
                    maps.KEYBIND_MAP,
                    {'hero_name': self.localizations[hero_key]},
                )
                parsed_info_section['Description'] = string_utils.format_description(
                    description, *format_vars
                )

            # some blocks might just be a description
            if 'm_vecAbilityPropertiesBlock' in info_section:
                main_block = self._parse_main_block(info_section, parsed_ability)
                parsed_info_section['Main'] = main_block

                # if attr not in parsed_ability:
                #     print(f'Missing base stat {attr}')
                #     continue
            # print(info_section)
            # side_props = info_section['m_vecBasicProperties']

            parsed_ui[f'Info{index+1}'] = parsed_info_section

        # remaining properties are placed into "Other"
        return parsed_ui

    def _parse_main_block(self, info_section, parsed_ability):
        main_block = {'Props': []}

        ability_prop_block = info_section['m_vecAbilityPropertiesBlock']
        if len(ability_prop_block) > 1:
            raise Exception(
                f'Expected only one ability property block, but found {len(ability_prop_block)}'
            )

        main_props = ability_prop_block[0]['m_vecAbilityProperties']

        title_key = ability_prop_block[0].get('m_strPropertiesTitleLocString')
        if title_key is not None:
            # localization keys are prefixed with a "#"
            title_key = title_key.replace('#', '')
            if title_key not in self.localizations:
                raise Exception(f'Missing title for key {title_key}')
            main_block['Title'] = self.localizations[title_key]

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
                print(f'[WARN] - {attr_key} is probably an upgrade attr that is not tagged as such')
                continue

            main_block['Props'].append(
                {'Name': self.localizations[attr_key + '_label'], 'Base': parsed_ability[attr_key]}
            )
        return main_block
