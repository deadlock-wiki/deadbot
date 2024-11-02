import subprocess
import os
import json
import utils.json_utils as json_utils
import shutil


class VersionParser:
    def __init__(
        self, output_dir, depot_downloader_dir, steam_username, steam_password, verbose=True
    ):
        self.app_id = '1422450'  # deadlock's app_id
        self.depot_id = '1422456'  # the big depot

        self.output_dir = output_dir
        self.depot_downloader_dir = depot_downloader_dir
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.verbose = verbose  # future proofing for verbose argument
        self.depot_downloader_output = os.path.join(self.output_dir, 'DepotDownloader')
        self.versions = {}
        self.versions_path = os.path.join(self.output_dir, 'versions.json')

    def _load(self):
        # Load versions to memory from versions.json
        versions_path = self.versions_path
        if os.path.exists(versions_path):
            with open(versions_path, 'r') as file:
                self.versions = json.load(file)
        else:
            raise Exception(f'Fatal error: {versions_path} not found')

        if self.verbose:
            print(f'Loaded {len(self.versions)} versions from {versions_path}')

    def _get_missing_versions(self):
        # Find empty manifestid's in the versions.json
        missing_versions = [
            manifest_id for manifest_id in self.versions if not self.versions[manifest_id]
        ]

        num_missing_versions = len(missing_versions)

        if self.verbose:
            print(f'Found {num_missing_versions} missing versions to parse')

        if num_missing_versions == 0:
            return {}

        return missing_versions

    def _parse(self, versions):
        parsed_versions = {}
        num_versions = len(versions)
        curr_num_versions = 0
        
        for manifest_id in versions:
            try:
                # Run the depot_downloader command
                subprocess_params = [
                    os.path.join(self.depot_downloader_dir, './DepotDownloader'),
                    '-app',
                    self.app_id,
                    '-depot',
                    self.depot_id,
                    '-manifest',
                    manifest_id,
                    '-username',
                    self.steam_username,
                    '-password',
                    self.steam_password,
                    '-remember-password',
                    '-filelist',
                    'input-data/steam_inf_path.txt',
                    '-dir',
                    self.depot_downloader_output,
                ]

                subprocess.run(
                    subprocess_params,
                    check=True,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                )
                steam_inf_path = os.path.join(
                    self.depot_downloader_output, 'game', 'citadel', 'steam.inf'
                )
                if not os.path.exists(steam_inf_path):
                    raise Exception(f'Fatal error: {steam_inf_path} not found')
            
            except Exception as e:
                print(f'Error occured while parsing manifest {manifest_id}, skipping')
                continue
                # Possible errors that cause exceptions include:
                # RateLimiting by Steam and
                # Manifest download being blocked by developers
                # Manifests before August 10th, 2024 are not available as they are under NDA
                # Skip the manifest and try the next one

            # Open steam inf
            with open(steam_inf_path, 'r') as file:
                steam_inf = file.read()

            parsed_versions[manifest_id] = {}

            # Parse each line
            for line in steam_inf.split('\n'):
                split_line = line.split('=')
                if len(split_line) != 2:
                    continue
                key = split_line[0]
                value = split_line[1]
                parsed_versions[manifest_id][key] = value

            curr_num_versions += 1

            if self.verbose:
                print(
                    f'({curr_num_versions}/{num_versions}): Parsed {manifest_id} '
                    +f'which contained VersionDate {parsed_versions[manifest_id]["VersionDate"]}'
                )

        if self.verbose:
            print(f'Parsed {len(parsed_versions)} new versions')

        return parsed_versions

    def _update(self, new_versions):
        # Merge the parsed versions with the existing versions
        self.versions.update(new_versions)

        if self.verbose:
            print(f'Updated {len(new_versions)} new versions')

    def _save(self):
        # Order by ServerVersion numerically (not lexicographically)
        # If a manifest is empty, it will be at the top
        self.versions = {
            k: v
            for k, v in sorted(
                self.versions.items(), key=lambda item: int(item[1].get('ServerVersion', 0))
            )
        }

        # Save the versions to versions.json
        json_utils.write(self.versions_path, self.versions)

        if self.verbose:
            print(f'Saved {len(self.versions)} versions to {self.versions_path}')

    def _clear_work_dir(self):
        # Clear the DepotDownloader directory
        shutil.rmtree(os.path.join(self.depot_downloader_output, '.DepotDownloader'))

        if self.verbose:
            print(f'Cleared {self.depot_downloader_output}')

    def run(self):
        self._load()

        missing_versions = self._get_missing_versions()
        if len(missing_versions) > 0:
            parsed_versions = self._parse(missing_versions)

            self._update(parsed_versions)

            self._save()

            self._clear_work_dir()
