import sys
import os
from os import listdir
from os.path import isfile, join

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from utils import json


class ChangelogParser:
    def __init__(self):
        print('Parsing changelogs...')
        self.CHANGELOGS_DIR = '../changelogs/'

    def run_all(self):
        files = [f for f in listdir(self.CHANGELOGS_DIR) if isfile(join(self.CHANGELOGS_DIR, f))]
        for file in files:
            self.run(file.replace('.txt', ''))

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

        json.write(self.OUTPUT_DIR + f'changelogs/{version}.json', changelog_dict)

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



if __name__ == '__main__':
    ChangelogParser().run_all()
