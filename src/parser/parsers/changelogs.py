import sys
import os
from os import listdir
from os.path import isfile, join
import datetime

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import utils.json_utils as json_utils

from .constants import OUTPUT_DIR
from .items import is_enabled


class ChangelogParser:
    def __init__(self, localization_data):
        self.CHANGELOGS_DIR = os.path.join(os.path.dirname(__file__), '../raw-changelogs/')
        self.OUTPUT_DIR = OUTPUT_DIR
        self.OUTPUT_CHANGELOGS = self.OUTPUT_DIR + '/changelogs'
        self.resources = self._get_resources()
        self.localization = localization_data #english
        self.default_tag = 'Other'
        self.unique_tags = [self.default_tag]
        self.unique_tag_groups = [self.default_tag]
        # i.e. Abilities is a tag group and a tag, Siphon Life is just a tag
        # i.e. Heroes is a tag group and a tag, Abrams is just a tag
        # all tags from a resource have icons embedded
        # only tag groups are displayed for /Changelogs page,
        # allowing users to see compact list of pages that have changelogs

    def run_all(self):
        changelogs_by_date = {}
        files = [f for f in listdir(self.CHANGELOGS_DIR) if isfile(join(self.CHANGELOGS_DIR, f))]
        for file in files:
            date = file.replace('.txt', '')
            changelog = self.run(date)
            changelogs_by_date[date] = changelog

        # take parsed changelogs and transform them into some other useful formats
        # self._create_resource_changelogs(changelogs_by_date)
        # self._create_changelog_db_data(changelogs_by_date)

        # print('Unique Tags:', self.unique_tags)
        print('Unique Tag Groups:', self.unique_tag_groups)

        # TESTING
        print(self.localization['CitadelCategoryWeapon'])

    def run(self, version):
        logs = self._read_logs(version)
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
                if resource_type == 'Items' and not is_enabled(resource):
                    continue

                # Determine if the line is about this resource
                # resource (i.e. hero) name in english is found in the line
                if resource_name in line:
                    tags = self._register_tag(tags, tag=resource_name, is_group_tag=False)

                    # Also register the resource type
                    tags = self._register_tag(tags, tag=resource_type)

                    # Also register 'Weapon Items', 'Spirit Items', etc. for item resources
                    # currently these are also a heading, this check makes it future proof
                    if resource_type == 'Items':
                        item_slot = resource['Slot']  # i.e. Tech
                        localized_item_slot = self.localization['CitadelCategory'+item_slot]
                        slot_str = localized_item_slot + ' Items'
                        tags = self._register_tag(tags, tag=slot_str)

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
                    line = '* ' + line[len(prefix):]

            changelog_out.append({'Description': line, 'Tags': tags})

        changelog_with_icons = changelog_out
        changelog_with_icons = self._embed_icons(changelog_out)

        json_utils.write(self.OUTPUT_CHANGELOGS + f'/date/{version}.json', changelog_with_icons)
        return changelog_with_icons

    def _heading_to_tag(self, heading):
        """
        Converts a heading to a tag, i.e. Hero and Heroes don't need to be separate tags,
        New Items doesn't need to be a tag at all, etc
        """

        # Remove ' Changes' suffix, i.e. 'Hero Changes' -> 'Heroes'
        heading = heading.replace(' Changes', '')

        map = {
            "Hero Gameplay": "Heroes",
            "Hero Gamepla": "Heroes",
            "Hero": "Heroes",
            "Item Gameplay": "Items",
            "New Items": "Items",
            "Misc Gameplay": self.default_tag,
            "General": self.default_tag,
            "General Change": self.default_tag
        }

        return map.get(heading, heading)

    # mass find and replace of any resource names with the ability icon template
    def _embed_icons(self, changelog):
        new_changelog = changelog.copy()
        for index, log in enumerate(changelog):
            tags = log['Tags']
            description = log['Description']
            for tag in tags:
                # resource_found = False
                # if tag in description:
                #     resource_found = True
                # if not resource_found:
                #     continue

                
                template = 'PageRef'

                icon = '{{' + template + '|' + tag + '}}'
                description = description.replace(tag, f'{icon} {tag}')
                new_changelog[index]['Description'] = description

        return new_changelog

    def _register_tag(self, tags, tag, is_group_tag=True):
        """
        Registers a tag to the changelog's unique current tags, 
        and to the static unique list of tags.
        """

        if tag not in tags:
            tags.append(tag)

        if tag not in self.unique_tags:
            self.unique_tags.append(tag)

        if is_group_tag and tag not in self.unique_tag_groups:
            self.unique_tag_groups.append(tag)

        return tags

    def _read_logs(self, version):
        # files just
        f = open(self.CHANGELOGS_DIR + f'{version}.txt', 'r', encoding='utf8')
        return f.read()

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

        return resources

    # Creates historic changelog for each resource (eg. heroes, items etc.)
    # using each parsed changelog
    def _create_resource_changelogs(self, changelogs_by_date):
        hero_changelogs = {}
        for date, changelog in changelogs_by_date.items():
            for hero, changes in changelog['Heroes'].items():
                if hero not in hero_changelogs:
                    hero_changelogs[hero] = {}
                hero_changelogs[hero][date] = changes

        for hero_name, changelog in hero_changelogs.items():
            json_utils.write(
                self.OUTPUT_CHANGELOGS + f'/hero/{hero_name}.json',
                self._sort_object_by_date_key(changelog),
            )

        item_changelogs = {}
        for date, changelog in changelogs_by_date.items():
            for item, changes in changelog['Items'].items():
                if item not in item_changelogs:
                    item_changelogs[item] = {}
                item_changelogs[item][date] = changes

        for item_name, changelog in item_changelogs.items():
            json_utils.write(
                self.OUTPUT_CHANGELOGS + f'/item/{item_name}.json',
                self._sort_object_by_date_key(changelog),
            )

    # Convert changelogs to an array of rows, with the plan to upload
    # them to a database (TODO)
    def _create_changelog_db_data(self, changelogs):
        rows = []
        for date, changelog in changelogs.items():
            for header, log_groups in changelog.items():
                for group_name, logs in log_groups.items():
                    for index, log in enumerate(logs):
                        changelog_row = {
                            'id': f'{header}-{group_name}-{index}',
                            'changelog': log,
                            'resource_key': group_name,
                            'resource_type': header,
                            'patch_version': '',
                            'timestamp': date,
                        }
                        rows.append(changelog_row)

        return rows

    def _sort_object_by_date_key(self, changelogs):
        sorted_keys = sorted(
            changelogs.keys(), key=lambda x: datetime.datetime.strptime(x, '%m-%d-%Y')
        )

        sorted_changelogs = {}
        for key in reversed(sorted_keys):
            sorted_changelogs[key] = changelogs[key]

        return sorted_changelogs


if __name__ == '__main__':
    ChangelogParser().run_all()
