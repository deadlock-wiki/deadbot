import sys
import os
from .ability_objects import AbilityUI
from ..hero.hero_objects import Hero

# bring parent modules in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.string_utils as string_utils


class AbilityUiParser:
    """
    Takes in parsed hero_data data (hero_data-data.json) and for each hero_data, format their abilities for
    display in the Wiki Ability Cards
    This is with the aim of matching the in-game layout

    Components of the ability card UI:

    *Info[x]* - Info section that contains a number of main attributes, sometimes with a description.
    Although rare, some abilities have multiple info sections.
    Info section contains:
    - *Main* - Main attributes of the ability
    - *Alt* - Other attributes that are displayed below the main ones
    - *Description* - Description of the info section

    *Upgrades* - The three upgrades that modify the ability

    Remaining data categories contain those that do not appear in Info[x].
    Important ones include *Cooldown* and *Charges*, as those are specifically shown in the
    top corners of the ability card
    """

    def __init__(self, abilities, language, localizations):
        self.abilities = abilities
        Hero.loadObjects()
        self.parsed_heroes = Hero.objects
        self.language = language
        self.localizations = localizations
        self.localization_updates = {}

    def run(self):
        output = {}
        for self.hero_key, hero in self.parsed_heroes.items():
            hero_data = hero.data
            # skip disabled heroes
            if hero_data['IsDisabled']:
                continue

            hero_abilities = {'Name': hero_data['Name']}
            for self.ability_index, ability in hero_data['BoundAbilities'].items():
                try:
                    parsed_ui = self._parse_ability_ui(ability)
                    if parsed_ui is not None:
                        hero_abilities[self.ability_index] = parsed_ui
                except Exception as e:
                    raise Exception(f'[ERROR] Failed to parse ui for ability {ability["Key"]}', e)

            output[self.hero_key] = hero_abilities

        # Only write to ability_ui.json for English
        if self.language == 'english':
            AbilityUI.hashToObjs(output)
            AbilityUI.saveObjects()

        return self.localization_updates

    def _parse_ability_ui(self, parsed_ability):
        parsed_ui = {
            'Key': parsed_ability['Key'],
            'Name': self._get_localized_string(parsed_ability['Key']),
        }

        ability_desc_key = parsed_ability['Key'] + '_desc'
        # some description keys are not found as they have a specific description per info section
        if ability_desc_key in self.localizations[self.language]:
            ability_desc = self._get_localized_string(parsed_ability['Key'] + '_desc')
            # required variables to insert into the description
            format_vars = (
                parsed_ability,
                maps.KEYBIND_MAP,
                {'ability_key': self.ability_index},
                {'hero_name': self._get_localized_string(self.hero_key)},
            )
            ability_desc = string_utils.format_description(ability_desc, *format_vars)
            parsed_ui['DescKey'] = ability_desc_key

            # update localization file with formatted description
            self.localization_updates[ability_desc_key] = ability_desc

        raw_ability = self.abilities[parsed_ability['Key']]

        # Some heroes do not have ui information, so are likely unplayable or in development
        # TODO - a check for if hero_data is in development to make sure
        if 'm_AbilityTooltipDetails' not in raw_ability:
            return None

        info_sections = raw_ability['m_AbilityTooltipDetails']['m_vecAbilityInfoSections']

        handled_keys = [
            'm_strAbilityPropertyUpgradeRequired',
            'm_vecAbilityPropertiesBlock',
            'm_strLocString',
            'm_vecBasicProperties',
        ]

        # track used attributes to avoid duplicate values in other categories
        self.used_attributes = ['Key', 'Name', 'Upgrades']
        for index, info_section in enumerate(info_sections):
            # skip any UI that requires an upgraded ability to display it
            if info_section.get('m_strAbilityPropertyUpgradeRequired') not in [None, '']:
                continue

            for key in info_section:
                if key not in handled_keys:
                    raise Exception(f'Unhandled key in info section {key}')

            # Each info section consists of some combination of
            # title, description, main properties, and alternate properties
            parsed_info_section = {
                'Main': None,
                'Alt': None,
            }

            desc_key = info_section.get('m_strLocString')
            if desc_key is not None and desc_key != '':
                # localization keys are prefixed with a "#", remove it
                if desc_key.startswith('#'):
                    desc_key = desc_key[len('#') :]
                else:
                    raise Exception(f'Invalid description key {desc_key}, expecting the # prefix')
                if desc_key in self.localizations[self.language]:
                    # raise Exception(f'Missing description for key {desc_key}')

                    description = self._get_localized_string(desc_key)
                    # required variables to insert into the description
                    format_vars = (
                        parsed_ability,
                        maps.KEYBIND_MAP,
                        {'ability_key': self.ability_index},
                        {'hero_name': self._get_localized_string(self.hero_key)},
                    )
                    parsed_info_section['DescKey'] = desc_key

                    description = string_utils.format_description(description, *format_vars)

                    # update localization file with formatted description
                    self.localization_updates[desc_key] = description

            # some blocks might just be a description
            if 'm_vecAbilityPropertiesBlock' in info_section:
                parsed_info_section['Main'] = self._parse_main_block(info_section, parsed_ability)

            if 'm_vecBasicProperties' in info_section:
                parsed_info_section['Alt'] = self._parse_alt_block(info_section, parsed_ability)

            parsed_ui[f'Info{index+1}'] = parsed_info_section

        parsed_ui['Upgrades'] = self._parse_upgrades(parsed_ability)

        parsed_ui.update(self._parse_rest_of_data(parsed_ability))

        return parsed_ui

    def _parse_main_block(self, info_section, parsed_ability):
        main_block = {'Props': []}

        props_block = info_section['m_vecAbilityPropertiesBlock']
        for props in props_block:
            title = None
            title_key = props.get('m_strPropertiesTitleLocString')
            if title_key is not None:
                title_key = title_key.replace('#', '')
                if title_key != '':
                    title = self._get_localized_string(title_key)

            ability_props = props['m_vecAbilityProperties']

            for ability_prop in ability_props:
                if title is None:
                    prop_object = {}
                else:
                    prop_object = {'Title': title}

                parsed_prop = self._parse_ability_prop(ability_prop)

                # skip property that requires ability to be upgraded
                if parsed_prop['requires_upgrade']:
                    continue

                attr_key = parsed_prop['key']
                if attr_key is None:
                    raise Exception(f"Missing value for ability {parsed_ability['Name']}")

                # This is probably an upgrade attr that is not tagged as such, so it will
                # not be shown in the main block
                if attr_key not in parsed_ability:
                    continue

                raw_ability = self._get_raw_ability_attr(parsed_ability['Key'], attr_key)

                prop_object.update(
                    {
                        'Key': attr_key,
                        'Name': self._get_localized_string(attr_key + '_label'),
                        'Value': parsed_ability[attr_key],
                    }
                )

                attr_type = raw_ability.get('m_strCSSClass')
                if attr_type is not None:
                    prop_object['Type'] = attr_type

                scale = self._get_scale(parsed_ability['Key'], attr_key)
                if scale is not None:
                    prop_object['Scale'] = scale
                self.used_attributes.append(attr_key)

                main_block['Props'].append(prop_object)

        return main_block

    def _parse_ability_prop(self, ability):
        attribute = {'key': None, 'requires_upgrade': False}

        for attr, value in ability.items():
            match attr:
                case 'm_strStatusEffectValue':
                    attribute['key'] = value

                case 'm_strImportantProperty':
                    # This is only used in case m_strStatusEffectValue is not found
                    if attribute['key'] is None:
                        attribute['key'] = value

                case 'm_bRequiresAbilityUpgrade':
                    attribute['requires_upgrade'] = True

                case 'm_bShowPropertyValue':
                    # this has no use at the moment, as we want to always show the prop value
                    continue

                case _:
                    print('[ERROR] Unhandled property', attr)

        return attribute

    def _parse_alt_block(self, info_section, parsed_ability):
        alt_block = []
        for prop in info_section['m_vecBasicProperties']:
            prop_object = {
                'Key': prop,
            }

            name = self._get_ability_display_name(prop)
            if name is not None:
                prop_object['Name'] = name

            prop_object['Value'] = parsed_ability.get(prop)

            attr_type = self._get_raw_ability_attr(parsed_ability['Key'], prop).get('m_strCSSClass')
            if attr_type is not None:
                prop_object['Type'] = attr_type

            scale = self._get_scale(parsed_ability['Key'], prop)
            if scale is not None:
                prop_object['Scale'] = scale

            alt_block.append(prop_object)

            self.used_attributes.append(prop)

        return alt_block

    def _parse_rest_of_data(self, parsed_ability):
        """
        Parse any data that has not been included in the main or alt block of the info section
        """
        rest_of_data = {
            'Cooldown': {},
            'Duration': {},
            'Range': {},
            'Cast': {},
            'Move': {},
            'Damage': {},
            'Health': {},
            'Buff': {},
            'Debuff': {},
            'Other': {},
        }

        for prop in parsed_ability:
            data = {
                'Name': self._get_ability_display_name(prop),
                'Value': parsed_ability.get(prop),
            }

            # These props are directly referenced and should live on the top level
            if prop in [
                'AbilityCharges',
                'AbilityCooldownBetweenCharge',
                'AbilityCooldown',
                'AbilityCastDelay',
                'AbilityCastRange',
                'AbilityDuration',
                'Radius',
            ]:
                rest_of_data[prop] = data
                continue

            # skip any attributes that are already placed in other categories
            if prop in self.used_attributes:
                continue

            raw_ability = self._get_raw_ability_attr(parsed_ability['Key'], prop)

            attr_type = raw_ability.get('m_strCSSClass')
            if attr_type is not None:
                data['Type'] = attr_type

            scale = self._get_scale(parsed_ability['Key'], prop)
            if scale is not None:
                data['Scale'] = scale

            match attr_type:
                case 'cooldown' | 'charge_cooldown':
                    rest_of_data['Cooldown'][prop] = data

                case 'duration':
                    rest_of_data['Duration'][prop] = data

                case 'range' | 'distance':
                    rest_of_data['Range'][prop] = data

                case 'damage' | 'bullet_damage' | 'tech_damage':
                    rest_of_data['Damage'][prop] = data

                case 'healing' | 'health':
                    rest_of_data['Health'][prop] = data

                case 'bullet_armor_up':
                    rest_of_data['Buff'][prop] = data

                case 'slow':
                    rest_of_data['Debuff'][prop] = data

                case 'cast':
                    rest_of_data['Cast'][prop] = data

                case 'move_speed':
                    rest_of_data['Move'][prop] = data

                case None | '':
                    rest_of_data['Other'][prop] = data
                case _:
                    raise Exception(f'Unhandled ability attr type {attr_type}')

        # Clear out any empty arrays
        cleared_data = {}
        for key, value in rest_of_data.items():
            if len(value) != 0:
                cleared_data[key] = value

        return cleared_data

    def _parse_upgrades(self, parsed_ability):
        parsed_upgrades = []
        for index, upgrade in enumerate(parsed_ability['Upgrades']):
            # Description key includes t1, t2, and t3 denoting the upgrade tier
            desc_key = f'{parsed_ability["Key"]}_t{index+1}_desc'

            # this key in particular is not accurate to the one in game
            ignore_desc_key = False
            if desc_key == 'citadel_ability_chrono_kinetic_carbine_t1_desc':
                ignore_desc_key = True

            if desc_key in self.localizations[self.language] and not ignore_desc_key:
                upgrade_desc = self._get_localized_string(desc_key)
                # required variables to insert into the description
                format_vars = (
                    upgrade,
                    maps.KEYBIND_MAP,
                    {'ability_key': self.ability_index},
                    {'hero_name': self._get_localized_string(self.hero_key)},
                )

                upgrade_desc = string_utils.format_description(upgrade_desc, *format_vars)

                # update localization file with formatted description
                self.localization_updates[desc_key] = upgrade_desc
                upgrade['DescKey'] = desc_key

            parsed_upgrades.append(upgrade)

        return parsed_upgrades

    def _get_scale(self, ability_key, attr):
        """
        Get scale data for the ability attribute, which will refer to how the value of the attribute
        scales with another stat, usually Spirit
        """
        raw_ability = self._get_raw_ability_attr(ability_key, attr)
        if 'm_subclassScaleFunction' in raw_ability:
            raw_scale = raw_ability['m_subclassScaleFunction']
            # Only include scale with a value, as not sure what
            # any others mean so far.
            if 'm_flStatScale' in raw_scale:
                return {
                    'Value': raw_scale['m_flStatScale'],
                    'Type': maps.get_scale_type(
                        raw_scale.get('m_eSpecificStatScaleType', 'ETechPower')
                    ),
                }

        return None

    def _get_uom(self, attr, value):
        """
        Extract unit of measurement for an attribute, either using the *[attr]_postfix* localization
        key, or if none exists, by checking the string value

        Example - If attribute has no localization key, but value is '53s'. Returns 's'
        """
        localized_key = f'{attr}_postfix'

        if localized_key in self.localizations[self.language]:
            return self._get_localized_string(localized_key)

        # Sometimes the uom is attached to the end of the value
        unit = ''
        if value.endswith('m'):
            unit = 'm'

        if value.endswith('s'):
            unit = 's'

        return unit

    def _get_ability_display_name(self, attr):
        """
        Returns localized string for the input attr, using '[attr]_label'

        For some edge cases, the localization key does not match this pattern
        and we defer to an override
        """
        localized_key = f'{attr}_label'
        if localized_key not in self.localizations[self.language]:
            return None

        return self._get_localized_string(localized_key)

    def _get_raw_ability_attr(self, ability_key, attr_key):
        return self.abilities[ability_key]['m_mapAbilityProperties'][attr_key]

    def _get_localized_string(self, key):
        OVERRIDES = {
            'MoveSlowPercent_label': 'MovementSlow_label',
            'BonusHealthRegen_label': 'HealthRegen_label',
            'BarbedWireRadius_label': 'Radius_label',
            'BarbedWireDamagePerMeter_label': 'DamagePerMeter_label',
            'BuildUpDuration_label': 'BuildupDuration_label',
            # capital "L" for some reason...
            'TechArmorDamageReduction_label': 'TechArmorDamageReduction_Label',
            'DamageAbsorb_label': 'DamageAbsorb_Label',
            'InvisRegen_label': 'InvisRegen_Label',
            'EvasionChance_label': 'EvasionChance_Label',
            'DelayBetweenShots_label': 'DelayBetweenShots_Label',
        }

        key = OVERRIDES.get(key, key)

        if key in self.localizations[self.language]:
            return self.localizations[self.language][key]

        # Default to English if not found in current language
        if key in self.localizations['english']:
            return self.localizations['english'][key]

        raise Exception(f'No localized string for key {key}')
