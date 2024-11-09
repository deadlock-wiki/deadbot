import os

import utils.json_utils as json_utils
from .tags import ChangelogTags as Tags


class ChangelogParser:
    def __init__(self, output_dir):
        self.OUTPUT_DIR = output_dir
        self.OUTPUT_CHANGELOGS = self.OUTPUT_DIR + '/changelogs'
        self.resources = self._get_resources()
        self.localization_en = self.get_lang_en()

        self.default_tag = 'Other'

        # list of all unique tags, including resource tags like Abrams/Basic Magazine
        self.unique_tags = [self.default_tag]

        # Retrieve tag lists and maps
        self.tags = Tags(self.default_tag, self.OUTPUT_CHANGELOGS)

    # Main
    def run_all(self, dict_changelogs):
        # take parsed changelogs and transform them into some other useful formats
        for version, changelog in dict_changelogs.items():
            self.run(version, changelog)

    # Parse a single changelog file
    def run(self, version, logs):
        changelog_lines = logs.split('\n')

        current_heading = ''
        changelog_out = []

        for line in changelog_lines:
            if line is None or line == '':
                continue

            # parse heading: if heading is found, update current heading
            if line.startswith('[ '):
                current_heading = line[2:-2]
                changelog_out.append(
                    {'Description': f'<h4>{current_heading}</h4>', 'Tags': [self.default_tag]}
                )
                continue

            # parse line:
            # replace hyphen with asterisk for bullet points on wiki
            prefixes = ['- ', ' - ']
            for prefix in prefixes:
                if line.startswith(prefix):
                    line = '* ' + line[len(prefix) :]
            # replace -> with →
            line = line.replace('->', '→')

            tags = self._parse_tags(current_heading, line)

            changelog_out.append({'Description': line, 'Tags': tags})

        changelog_with_icons = self._embed_icons(changelog_out)
        os.makedirs(self.OUTPUT_CHANGELOGS, exist_ok=True)
        json_utils.write(self.OUTPUT_CHANGELOGS + f'/versions/{version}.json', changelog_with_icons)
        return changelog_with_icons

    # Parse a given line for assignable tags
    def _parse_tags(self, current_heading, line):
        tags = []

        # find if a resource can be assigned a changelog line
        for resource_key in self.resources:
            resource = self.resources[resource_key]
            resource_type = resource['Type']
            resource_name = resource['Name']

            if resource_name is None:
                continue

            # Skip these disabled items as they are often confused with a stat
            if resource_name in ['Fire Rate', 'Health Regen']:
                continue

            if resource_name in line:
                tags = self._register_tag(tags, tag=resource_name)

                # Also register the resource type
                tags = self._register_tag(tags, tag=resource_type)

                # Also register 'Weapon Item', 'Spirit Item', etc. for item resources
                # currently these are also a heading, this check makes it future proof
                if resource_type == 'Item':
                    item_slot = resource['Slot']  # i.e. Tech
                    localized_item_slot = self.localization_en['CitadelCategory' + item_slot]
                    slot_str = localized_item_slot + ' Item'
                    tags = self._register_tag(tags, tag=slot_str)

                # If its an ability, register the hero as well
                if resource_type == 'Ability':
                    hero = self.get_hero_from_ability(resource_key)
                    if hero is not None:
                        tags = self._register_tag(tags, tag=hero)

        # Use specified lists to match for possible tags
        for tag in self.tags.match_text:
            if tag in line:
                tags = self._register_tag(tags, tag)
        for tag in self.tags.match_word:
            if tag in line.split(' '):
                tags = self._register_tag(tags, tag)

        # Also register heading as a tag
        if current_heading != '':
            # Remove ' Changes' suffix, i.e. 'Hero Changes' -> 'Hero'
            heading_tag = current_heading.replace(' Changes', '')

            for resource_key, resource_data in self.resources.items():
                resource_name = resource_data['Name']

            if heading_tag is not None:
                tags = self._register_tag(tags, tag=heading_tag)

            # If the heading is a "HeroLab <hero>", register <hero> as well
            if current_heading.startswith('HeroLab '):
                hero = current_heading[len('HeroLab ') :]
                if self.is_hero(hero):
                    tags = self._register_tag(tags, hero)
                    tags = self._register_tag(tags, 'Hero')

        # if no tag is found, assign to default tag
        if len(tags) == 0:
            tags = self._register_tag(tags, tag=self.default_tag)

        # Remove default tag if its not the only tag
        # without this, default tag may be added occasionally
        # on accident if its a remapped result of a heading
        if len(tags) > 1 and self.default_tag in tags:
            tags.remove(self.default_tag)

        return tags

    def _register_tag(self, tags, tag):
        """
        Registers a tag to the changelog's current unique tags,
        and to the static unique list of tags.
        """

        # Remap tag
        tag = self._remap_tag(tag)
        if tag is None:
            return tags

        # Assign its parents
        tags = self._assign_parents(tags, tag)

        # Add tag
        if tag not in tags:
            tags.append(tag)

        # Add to unique lists
        if tag not in self.unique_tags:
            self.unique_tags.append(tag)

        return tags

    def _remap_tag(self, tag):
        """
        Remaps tags as necessary, i.e.
        'Hero Gameplay' -> 'Hero',
        'New Items' -> 'Item'
        """

        if tag in self.tags.ignore_list:
            return None

        return self.tags.remap.get(tag, tag)

    def _assign_parents(self, tags, tag):
        """
        Assigns a tag's parents to the list of tags
        """

        if tag in self.tags.parent_lookup:
            for parent in self.tags.parent_lookup[tag]:
                tags = self._register_tag(tags, parent)

        return tags

    # mass find and replace of referenced tags and
    # their remap-sources to {{PageRef|tag|alt_name=remap-source}}
    def _embed_icons(self, changelog):
        new_changelog = changelog.copy()
        for index, log in enumerate(changelog):
            tags = log['Tags']
            description = log['Description']
            remaining_description = description

            # Check for tags that are in the description
            for tag in tags:
                template = 'PageRef'

                icon = '{{' + template + '|' + tag + '}}'

                if tag in remaining_description:
                    description = description.replace(tag, icon)
                    new_changelog[index]['Description'] = description

                    # Remove it from the remaining description so that similarly named tags
                    # don't get embedded inside the icon, i.e. preventing
                    # {{PageRef|Heavy {{PageRef|Barrage}}}} from happening
                    # when tags Barrage and Heavy Barrage are present
                    # Most cases of this will still require manual fixing after its uploaded
                    # though some are correct as is, such as 'Paradox' and 'Paradoxical Swap'
                    remaining_description = remaining_description.replace(tag, '')

            # Check for remappable_texts that are in the description that
            # map to a tag that's in the tags list
            # if so, add the icon with alt_name param
            # {{PageRef|tag|alt_name=remappable_text}}
            for remappable_text in self.tags.remap:
                tag = self.tags.remap[remappable_text]
                if remappable_text in remaining_description and tag in tags:
                    icon = '{{' + template + '|' + tag + '|alt_name=' + remappable_text + '}}'
                    description = description.replace(remappable_text, icon)
                    remaining_description = remaining_description.replace(remappable_text, '')
                    new_changelog[index]['Description'] = description

        return changelog

    def _get_resources(self):
        resources = {}
        heroes = json_utils.read(self.OUTPUT_DIR + '/json/hero-data.json')
        items = json_utils.read(self.OUTPUT_DIR + '/json/item-data.json')
        abilities = json_utils.read(self.OUTPUT_DIR + '/json/ability-data.json')

        for key in heroes:
            heroes[key]['Type'] = 'Hero'

        for key in items:
            items[key]['Type'] = 'Item'

        for key in abilities:
            abilities[key]['Type'] = 'Ability'

        resources.update(heroes)
        resources.update(items)
        resources.update(abilities)

        # Order the resources by the length of their name, longest to shortest
        # This makes longer names take precedence over shorter ones
        # i.e. check for Smoke Bomb before checking for Smoke
        # handle name being None
        resources = dict(sorted(resources.items(), 
                                key=lambda x: len(x[1]['Name']) 
                                if x[1]['Name'] is not None else 0, reverse=True))

        self.heroes = heroes

        return resources

    def is_hero(self, tag):
        """
        Returns True if the tag is a hero name i.e. Abrams
        """
        for hero_key, hero_data in self.heroes.items():
            hero_name = hero_data['Name']
            if tag == hero_name:
                return True

        return False

    # Given an ability key, return the first hero that has that ability
    def get_hero_from_ability(self, ability_key_to_search):
        for hero_key in self.heroes:
            hero = self.heroes[hero_key]
            for _, ability_data in hero['BoundAbilities'].items():
                if ability_data['Key'] == ability_key_to_search:
                    return self.localization_en[hero_key]

        return None

    def get_lang_en(self):
        return json_utils.read(self.OUTPUT_DIR + '/localizations/english.json')
