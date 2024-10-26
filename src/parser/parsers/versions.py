import subprocess
import os
import json

class VersionParser:
    

    def __init__(self, output_dir, depot_downloader_cmd, steam_username, steam_password):
        self.app_id = '1422450' #deadlock's app_id
        self.depot_id = '1422456' #the big depot

        self.output_dir = output_dir
        self.depot_downloader_cmd = depot_downloader_cmd
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.versions = {}

    def load_versions(self):
        # Load versions to memory from versions.json
        versions_path = os.path.join(self.output_dir, 'json', 'versions.json')
        if os.path.exists(versions_path):
            with open(versions_path, 'r') as file:
                self.versions = json.load(file)
        else:
            #print('No versions.json found, run --parse_versions', e)
            raise Exception('No json/versions.json found')
            




    def run(self):
        self.load_versions()
        print(f'Parsing missing versions with {self.depot_downloader_cmd}...')

        