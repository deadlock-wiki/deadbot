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

        # Tags to register if they are found in the changelog line
        self.tags_match_text = [
            'Trooper',
            'Guardian',
            'Walker',
            'Patron',
            'Weakened Patron',
            'Weakened patron'
            'Shrine',
            'Mid-Boss',
            'Midboss',
            'MidBoss',
            'Mid Boss',
            'Mid boss',
            'Map',
            'Rejuvenator' 'Creep',
            'Neutral',
            'Denizen',
        ]
        self.tags_match_word = ['creep', 'neutral', 'creeps', 'neutrals', 'Rejuv']

        # texts in this list are not converted to tags
        # useful when they are otherwise added due to being a heading
        self.tags_to_ignore = ['Ranked Mode']

        # remaps tags to a more general tag
        self.tag_remap  = {
            'Hero Gameplay': 'Heroes',
            'Hero Gamepla': 'Heroes',
            'Hero': 'Heroes',
            'Item Gameplay': 'Items',
            'New Items': 'Items',
            'Misc Gameplay': self.default_tag,
            'Misc Gamepla': self.default_tag,
            'General': self.default_tag,
            'General Change': self.default_tag,
            'MidBoss': 'Mid-Boss',
            'Midboss': 'Mid-Boss',
            'Mid Boss': 'Mid-Boss',
            'Mid boss': 'Mid-Boss',
            'Weakened patron': 'Weakened Patron',
            'Rejuv': 'Rejuvenator',
            'creep': 'Creep',
            'creeps': 'Creep',
            'neutral': 'Denizen',
            'neutrals': 'Denizen',
            'Neutral': 'Denizen',
        }

        # tags below are after _remap_tag() is called
        # key = child
        # value = parents to assign
        # child, [parents] instead of parent, [children] for easier lookup
        self.tag_parents = {
            'Denizen': ['NPC', 'Creep'],
            'Creep': ['NPC'],
            'Trooper': ['Base Defenses', 'NPC', 'Creep'],
            'Guardian': ['Base Defenses', 'NPC'],
            'Walker': ['Base Defenses', 'NPC'],
            'Patron': ['Base Defenses'],
            'Weakened Patron': ['Patron', 'Base Defenses'],
            'Shrine': ['Base Defenses'],
            'Mid-Boss': ['NPC'],
            'Weapon Items': ['Items'],
            'Vitality Items': ['Items'],
            'Spirit Items': ['Items'],
            'Abilities': ['Heroes'],
        }

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

            # parse heading: if heading is found, update current heading
            if line.startswith('[ '):
                current_heading = line[2:-2]
                changelog_out.append({'Description': f'<h4>{current_heading}</h4>', 'Tags': []})
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

    def _parse_tags(self, current_heading, line):
        tags = []

        # find if a resource can be assigned a changelog line
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

        
        for tag in self.tags_match_text:
            if tag in line:
                tags = self._register_tag(tags, tag)
        for tag in self.tags_match_word:
            if tag in line.split(' '):
                tags = self._register_tag(tags, tag)

        # Also register heading as a tag
        if current_heading != '':
            # Remove ' Changes' suffix, i.e. 'Hero Changes' -> 'Heroes'
            heading_tag = current_heading.replace(' Changes', '')
            if heading_tag is not None:
                tags = self._register_tag(tags, tag=heading_tag)

        # if no tag is found, assign to default tag
        if len(tags) == 0:
            tags = self._register_tag(tags, tag=self.default_tag)

        # Remove default tag if its not the only tag
        # otherwise, default tag may be added occasionally if its a heading
        if len(tags) > 1 and self.default_tag in tags:
            tags.remove(self.default_tag)

        return tags

    def _assign_parents(self, tags, tag):
        """
        Assigns a tag's parents to the list of tags
        """

        if tag in self.tag_parents:
            for parent in self.tag_parents[tag]:
                tags = self._register_tag(tags, parent)

        return tags

    def _remap_tag(self, tag):
        """
        Remaps tags as necessary, i.e. 
        'Hero Gameplay' -> 'Heroes',
        'New Items' -> 'Items'
        """

        if tag in self.tags_to_ignore:
            return None

        return self.tag_remap.get(tag, tag)

    def _register_tag(self, tags, tag, is_group_tag=True):
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
            unique_tag_groups = sorted(unique_tag_groups)
            if existing_tag_groups != unique_tag_groups:
                print(
                    f'WARNING: Unique tag groups in {tag_groups_path} are '
                    + 'different from existing tag groups. \n'
                    + 'Clean up any new ones if necessary by referring to '
                    + 'ChangelogParser._parse_tags(). '
                    + 'If a new unique group tag is to be added, '
                    + 'add it to deadlocked.wiki/Template:Changelogs Navbox'
                )

        # Write the new ones to file
        json_utils.write(tag_groups_path, unique_tag_groups)

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
