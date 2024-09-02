import sys
import os
from os import listdir
from os.path import isfile, join
import datetime 

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json


class ChangelogParser:
    def __init__(self):
        print('Parsing changelogs...')
        self.CHANGELOGS_DIR = './changelogs/'
        self.PARSED_CHANGELOGS_DIR = './parsed-changelogs/'
        self.OUTPUT_DIR = '../../output-data/'

    def run_all(self):
        changelogs_by_date = {}
        files = [f for f in listdir(self.CHANGELOGS_DIR) if isfile(join(self.CHANGELOGS_DIR, f))]
        for file in files:
            date = file.replace('.txt', '')
            changelog = self.run(date)
            changelogs_by_date[date] = changelog

        self._create_resource_changelogs(changelogs_by_date)

    def run(self, version):
        logs = self._read_logs(version)
        resources = self._get_resources()

        changelog_lines = logs.split('\n')

        current_heading = 'Other'
        default_category = 'General'
        changelog_dict = {current_heading: {default_category: []}, 'Heroes': {default_category: []}, 'Items': {default_category: []}}

        for line in changelog_lines:
            if line is None or line == '':
                continue

            # if heading is found, update current heading
            if line.startswith('[ '):
                current_heading = line[2:-2]
                changelog_dict[current_heading] = {default_category: []}
                continue

            # find if a resource can be assigned a changelog line
            resource_found = False
            for resource_key in resources:
                resource = resources[resource_key]
                resource_type = resource['Type']
                resource_name = resource['Name']
                if resource['Name'] is None:
                    continue

                if resource['Name'] in line:
                    resource_found = True
                    if resource_name not in changelog_dict[resource_type]:
                        changelog_dict[resource_type][resource_name] = []

                    # strip redundant prefix as it is already grouped under resource_name
                    if line.startswith(f'- {resource_name}: '):
                        line = line.replace(f'{resource_name}: ', '')

                    changelog_dict[resource_type][resource_name].append(line)

            if not resource_found:
                changelog_dict[current_heading]['General'].append(line)

        json.write(self.PARSED_CHANGELOGS_DIR + f'date/{version}.json', changelog_dict)
        return changelog_dict

    def _read_logs(self, version):
        # files just
        f = open(self.CHANGELOGS_DIR + f'{version}.txt', 'r', encoding='utf8')
        return f.read()
    
    def _get_resources(self):
        resources = {}
        heroes = json.read(self.OUTPUT_DIR + 'json/hero-data.json')
        items = json.read(self.OUTPUT_DIR + 'json/item-data.json')

        for key in heroes:
            heroes[key]['Type'] = 'Heroes'

        for key in items:
            items[key]['Type'] = 'Items'

        resources.update(heroes)
        resources.update(items)

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
            json.write(self.PARSED_CHANGELOGS_DIR + f'hero/{hero_name}.txt', self._sort_object_by_date_key(changelog))

        item_changelogs = {}
        for date, changelog in changelogs_by_date.items():
            for item, changes in changelog['Items'].items():
                if item not in item_changelogs:
                    item_changelogs[item] = {}
                item_changelogs[item][date] = changes
        
        for item_name, changelog in item_changelogs.items():
            json.write(self.PARSED_CHANGELOGS_DIR + f'item/{item_name}.txt', self._sort_object_by_date_key(changelog))

    def _sort_object_by_date_key(self, changelogs):
        sorted_keys = sorted(changelogs.keys(), key=lambda x: datetime.datetime.strptime(x, '%m-%d-%Y'))
    
        sorted_changelogs = {}
        for key in reversed(sorted_keys):
            sorted_changelogs[key] = changelogs[key]

        return sorted_changelogs

if __name__ == '__main__':
    ChangelogParser().run_all()
