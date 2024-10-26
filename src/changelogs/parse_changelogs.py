import os

import utils.json_utils as json_utils


class ChangelogParser:
    def __init__(self, output_dir):
        self.OUTPUT_DIR = output_dir
        self.OUTPUT_CHANGELOGS = self.OUTPUT_DIR + '/changelogs'
        self.resources = self._get_resources()
        self.localization_en = self.get_lang_en()

        self.default_tag = 'Other'
        self.unique_tags = [self.default_tag]
        self.unique_tag_groups = [self.default_tag]

    def run_all(self, dict_changelogs):
        # take parsed changelogs and transform them into some other useful formats
        for version, changelog in dict_changelogs.items():
            self.run(version, changelog)

        self._write_unique_tag_groups(self.unique_tag_groups)

    def run(self, version, logs):
        changelog_lines = logs.split('\n')

        current_heading = ''
        changelog_out = []

        for line in changelog_lines:
            if line is None or line == '':
                continue

            # if heading is found, update current heading
            if line.startswith('[ '):
                current_heading = line[2:-2]
                continue

            # find if a resource can be assigned a changelog line
            tags = []
            for resource_key in self.resources:
                resource = self.resources[resource_key]
                resource_type = resource['Type']
                resource_name = resource['Name']

                if resource_name is None:
                    continue

                # Skip disabled items
                if resource_type == 'Items' and resource.get('Disabled', False):
                    continue

                if resource_name in line:
                    tags = self._register_tag(tags, tag=resource_name, is_group_tag=False)

                    # Also register the resource type
                    tags = self._register_tag(tags, tag=resource_type)

                    # Also register 'Weapon Items', 'Spirit Items', etc. for item resources
                    # currently these are also a heading, this check makes it future proof
                    if resource_type == 'Items':
                        item_slot = resource['Slot']  # i.e. Tech
                        localized_item_slot = self.localization_en['CitadelCategory' + item_slot]
                        slot_str = localized_item_slot + ' Items'
                        tags = self._register_tag(tags, tag=slot_str)

                    # If its an ability, register the hero as well
                    if resource_type == 'Abilities':
                        hero = self.get_hero_from_ability(resource_key)
                        if hero is not None:
                            tags = self._register_tag(tags, tag=hero, is_group_tag=False)
                            tags = self._register_tag(tags, tag='Heroes')

            # check for other tags
            # all tags in this are counted as a tag group
            tags_to_search = ['Map']
            for tag_to_search in tags_to_search:
                if tag_to_search in line:
                    tags = self._register_tag(tags, tag=tag_to_search)

            # Also register heading as a tag
            if current_heading != '':
                heading_tag = self._heading_to_tag(current_heading)
                if heading_tag is not None:
                    tags = self._register_tag(tags, tag=heading_tag)

            # if no tag is found, assign to default group
            if len(tags) == 0:
                tags = self._register_tag(tags, tag=self.default_tag)

            # Replace hyphen with asterisk for bullet points on wiki
            prefixes = ['- ', ' - ']
            for prefix in prefixes:
                if line.startswith(prefix):
                    line = '* ' + line[len(prefix) :]

            # Remove default tag if its not the only tag
            if len(tags) > 1 and self.default_tag in tags:
                tags.remove(self.default_tag)

            changelog_out.append({'Description': line, 'Tags': tags})

        changelog_with_icons = self._embed_icons(changelog_out)
        os.makedirs(self.OUTPUT_CHANGELOGS, exist_ok=True)
        json_utils.write(self.OUTPUT_CHANGELOGS + f'/versions/{version}.json', changelog_with_icons)
        return changelog_with_icons

    def _heading_to_tag(self, heading):
        """
        Converts a heading to a tag, i.e. Hero and Heroes don't need to be separate tags,
        New Items doesn't need to be a tag at all, etc
        """

        # Remove ' Changes' suffix, i.e. 'Hero Changes' -> 'Heroes'
        heading = heading.replace(' Changes', '')

        map = {
            'Hero Gameplay': 'Heroes',
            'Hero Gamepla': 'Heroes',
            'Hero': 'Heroes',
            'Item Gameplay': 'Items',
            'New Items': 'Items',
            'Misc Gameplay': self.default_tag,
            'General': self.default_tag,
            'General Change': self.default_tag,
        }

        # headings in this list are not converted to tags
        headings_to_ignore = ['Ranked Mode']
        if heading in headings_to_ignore:
            return None

        return map.get(heading, heading)

    def _register_tag(self, tags, tag, is_group_tag=True):
        """
        Registers a tag to the changelog's current unique tags,
        and to the static unique list of tags.
        """

        if tag not in tags:
            tags.append(tag)

        if tag not in self.unique_tags:
            self.unique_tags.append(tag)

        if is_group_tag and tag not in self.unique_tag_groups:
            self.unique_tag_groups.append(tag)

        return tags

    # mass find and replace of referenced tags to {{PageRef|tag}}
    def _embed_icons(self, changelog):
        new_changelog = changelog.copy()
        for index, log in enumerate(changelog):
            tags = log['Tags']
            description = log['Description']
            remaining_description = description
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

        return changelog

    def _write_unique_tag_groups(self, unique_tag_groups):
        # Read existing tag groups
        tag_groups_path = self.OUTPUT_CHANGELOGS + '/tag_groups.json'
        if os.path.exists(tag_groups_path):
            existing_tag_groups = json_utils.read(tag_groups_path)

            # Print a warning if the data is different
            if existing_tag_groups != unique_tag_groups:
                print(
                    'WARNING: Unique tag groups are different from existing tag groups. \n'
                    + 'Clean up any new ones if necessary by referring to '
                    + 'ChangelogParser.run(). '
                    + 'If a new unique group tag is to be added, '
                    + 'add it to deadlocked.wiki/Template:Changelogs Navbox'
                )

        # Write the new ones to file
        json_utils.write(tag_groups_path, sorted(unique_tag_groups))

    def _get_resources(self):
        resources = {}
        heroes = json_utils.read(self.OUTPUT_DIR + '/json/hero-data.json')
        items = json_utils.read(self.OUTPUT_DIR + '/json/item-data.json')
        abilities = json_utils.read(self.OUTPUT_DIR + '/json/ability-data.json')

        for key in heroes:
            heroes[key]['Type'] = 'Heroes'

        for key in items:
            items[key]['Type'] = 'Items'

        for key in abilities:
            abilities[key]['Type'] = 'Abilities'

        resources.update(heroes)
        resources.update(items)
        resources.update(abilities)

        self.heroes = heroes
        self.items = items
        self.abilities = abilities

        return resources

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
