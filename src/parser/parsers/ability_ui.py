import sys
import os

# bring parent modules in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.string_utils as string_utils
import utils.num_utils as num_utils


class AbilityUiParser:
    def __init__(self, abilities, parsed_heroes, localizations):
        self.abilities = abilities
        self.parsed_heroes = parsed_heroes
        self.localizations = localizations

    def run(self):
        output = {}
        for self.hero_key, hero in self.parsed_heroes.items():
            hero_abilities = {}
            for self.ability_index, ability in hero['BoundAbilities'].items():
                try:
                    parsed_ui = self._parse_ability_ui(ability)
                    if parsed_ui is not None:
                        hero_abilities[self.ability_index] = parsed_ui
                except Exception as e:
                    raise Exception(f'[ERROR] Failed to parse ui for ability {ability["Key"]}', e)

            output[self.hero_key] = hero_abilities

        return output

    def _parse_ability_ui(self, parsed_ability):
        parsed_ui = {
            'Name': self.localizations.get(parsed_ability['Key']),
            'Key': parsed_ability['Key'],
            'Upgrades': [],
        }

        ability_desc_key = parsed_ability['Key'] + '_desc'
        # some description keys are not found as they have a specific description per info section
        if ability_desc_key in self.localizations:
            ability_desc = self.localizations[parsed_ability['Key'] + '_desc']
            # required variables to insert into the description
            format_vars = (
                parsed_ability,
                maps.KEYBIND_MAP,
                {'hero_name': self.localizations[self.hero_key]},
            )
            ability_desc = string_utils.format_description(ability_desc, *format_vars)
            parsed_ui['Description'] = ability_desc

        parsed_ui['Upgrades'] = self._parse_upgrades(parsed_ability)

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

        # track used attributes to see what should be put in the "Other" category
        self.used_attributes = ['Key', 'Name', 'Upgrades']
        for index, info_section in enumerate(info_sections):
            if parsed_ability['Key'] == 'viscous_goo_grenade':
                print(index)
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
            if desc_key is not None and desc_key != '':
                # localization keys are prefixed with a "#"
                desc_key = desc_key.replace('#', '')
                if desc_key in self.localizations:
                    # raise Exception(f'Missing description for key {desc_key}')

                    description = self.localizations[desc_key]
                    # required variables to insert into the description
                    format_vars = (
                        parsed_ability,
                        maps.KEYBIND_MAP,
                        {'hero_name': self.localizations[self.hero_key]},
                    )
                    parsed_info_section['Description'] = string_utils.format_description(
                        description, *format_vars
                    )

            # some blocks might just be a description
            if 'm_vecAbilityPropertiesBlock' in info_section:
                parsed_info_section['Main'] = self._parse_main_block(info_section, parsed_ability)

                # if attr not in parsed_ability:
                #     print(f'Missing base stat {attr}')
                #     continue

            if 'm_vecBasicProperties' in info_section:
                parsed_info_section['Alt'] = self._parse_alt_block(info_section, parsed_ability)

            parsed_ui[f'Info{index+1}'] = parsed_info_section

        parsed_ui['Other'] = self._parse_other_block(info_section, parsed_ability)

        # remaining properties are placed into "Other"
        return parsed_ui

    def _parse_main_block(self, info_section, parsed_ability):
        main_block = {'Props': []}

        ability_prop_block = info_section['m_vecAbilityPropertiesBlock']
        # if len(ability_prop_block) > 1:
        # raise Exception(
        #     f'Expected only one ability property block, but found {len(ability_prop_block)} for
        # ability {parsed_ability["Key"]}'
        # )

        main_props = ability_prop_block[0]['m_vecAbilityProperties']

        title_key = ability_prop_block[0].get('m_strPropertiesTitleLocString')
        if title_key is not None:
            # localization keys are prefixed with a "#"
            title_key = title_key.replace('#', '')
            if title_key != '':
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

            raw_ability = self._get_raw_ability_attr(parsed_ability['Key'], attr_key)

            prop = {
                'Name': self.localizations[attr_key + '_label'],
                'Value': parsed_ability[attr_key],
                'Type': raw_ability.get('m_strCSSClass'),
            }

            if 'm_subclassScaleFunction' in raw_ability:
                raw_scale = raw_ability['m_subclassScaleFunction']
                # Only include scaler with a value, as not sure what
                # any others mean so far.
                if 'm_flStatScale' in raw_scale:
                    prop['Scaler'] = {
                        'Value': raw_scale['m_flStatScale'],
                        'Type': maps.get_scaler_type(
                            raw_scale.get('m_eSpecificStatScaleType', 'ETechPower')
                        ),
                    }

            main_block['Props'].append(prop)

            self.used_attributes.append(attr_key)
        return main_block

    def _parse_alt_block(self, info_section, parsed_ability):
        alt_block = []
        for prop in info_section['m_vecBasicProperties']:
            alt_block.append(
                {
                    'Name': self._get_ability_display_name(prop),
                    'Value': parsed_ability.get(prop),
                    'Type': self._get_raw_ability_attr(parsed_ability['Key'], prop).get(
                        'm_strCSSClass'
                    ),
                }
            )

            self.used_attributes.append(prop)

        return alt_block

    def _parse_other_block(self, info_section, parsed_ability):
        other_block = []
        for prop in parsed_ability:
            # skip any attributes that are already placed in other categories
            if prop in self.used_attributes:
                continue

            raw_ability = self._get_raw_ability_attr(parsed_ability['Key'], prop)
            other_block.append(
                {
                    'Name': self._get_ability_display_name(prop),
                    'Value': parsed_ability.get(prop),
                    'Type': raw_ability.get('m_strCSSClass'),
                }
            )
        return other_block

    def _parse_upgrades(self, parsed_ability):
        parsed_upgrades = []
        for upgrade in parsed_ability['Upgrades']:
            if 'DescKey' not in upgrade:
                description = self._create_description(upgrade)
            else:
                upgrade_desc = self.localizations[upgrade['DescKey']]
                # required variables to insert into the description
                format_vars = (
                    upgrade,
                    maps.KEYBIND_MAP,
                    {'ability_key': self.ability_index},
                    {'hero_name': self.localizations[self.hero_key]},
                )

                upgrade_desc = string_utils.format_description(upgrade_desc, *format_vars)
                description = upgrade_desc
                del upgrade['DescKey']

            upgrade['Description'] = description
            parsed_upgrades.append(upgrade)

        return parsed_upgrades

    def _create_description(self, upgrade):
        desc = ''
        for attr, value in upgrade.items():
            str_value = str(value)

            uom = self._get_uom(attr, str_value)

            # update data value to have no unit of measurement
            num_value = num_utils.remove_uom(str_value)

            prefix = ''
            # attach "+" if the value is positive
            if isinstance(value, str) or not value < 0:
                prefix = '+'

            desc += f'{prefix}{num_value}{uom} {self._get_ability_display_name(attr)} and '

        # strip off extra "and" from description
        desc = desc[: -len(' and ')]
        return desc

    def _get_uom(self, attr, value):
        localized_key = f'{attr}_postfix'

        if localized_key in self.localizations:
            return self.localizations[localized_key]

        # Sometimes the uom is attached to the end of the value
        unit = ''
        if value.endswith('m'):
            unit = 'm'

        if value.endswith('s'):
            unit = 's'

        return unit

    def _get_ability_display_name(self, attr):
        OVERRIDES = {
            'BonusHealthRegen': 'HealthRegen_label',
            'BarbedWireRadius': 'Radius_label',
            'BarbedWireDamagePerMeter': 'DamagePerMeter_label',
            'BuildUpDuration': 'BuildupDuration_label',
            # capital "L" for some reason...
            'TechArmorDamageReduction': 'TechArmorDamageReduction_Label',
            'DamageAbsorb': 'DamageAbsorb_Label',
            'InvisRegen': 'InvisRegen_Label',
            'EvasionChance': 'EvasionChance_Label',
            'DelayBetweenShots': 'DelayBetweenShots_Label',
        }

        if attr in OVERRIDES:
            return self.localizations[OVERRIDES[attr]]

        localized_key = f'{attr}_label'
        if localized_key not in self.localizations:
            print(f'Missing label for key {localized_key}')
            return attr
        return self.localizations[localized_key]

    def _get_raw_ability_attr(self, ability_key, attr_key):
        return self.abilities[ability_key]['m_mapAbilityProperties'][attr_key]
