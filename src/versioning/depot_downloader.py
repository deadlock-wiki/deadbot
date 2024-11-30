import subprocess
import os
import json
import utils.json_utils as json_utils
from utils.game_utils import load_game_info
import shutil
from constants import APP_ID, DEPOT_ID


class DepotDownloader:
    def __init__(
        self, output_dir, depot_downloader_dir, steam_username, steam_password, verbose=True
    ):
        self.app_id = APP_ID  # deadlock's app_id
        self.depot_id = DEPOT_ID  # the big depot

        self.output_dir = output_dir
        self.depot_downloader_dir = depot_downloader_dir
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.verbose = verbose  # future proofing for verbose argument
        self.depot_downloader_output = 'deadlock-data'
        self.versions = {}
        self.versions_path = os.path.join(self.output_dir, 'versions.json')

    def _download(self, manifest_id):
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
                'input-data/depot_downloader_file_list.txt',  # module requires it passed via file
                '-dir',
                self.depot_downloader_output,
            ]

            result = subprocess.run(
                subprocess_params,
                check=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
            )
            steam_inf_path = os.path.join(
                self.depot_downloader_output, 'game', 'citadel', 'steam.inf'
            )
            print('DepotDownloader output: ' + result.stdout)
            if not os.path.exists(steam_inf_path):
                raise Exception(f'Fatal error: {steam_inf_path} not found')

        except Exception as e:
            raise Exception(f'Error occured while parsing manifest {manifest_id}, error: {e}')
            # Possible errors that cause exceptions include:
            # RateLimiting by Steam
            # Manifest download being blocked by developers
            # Manifests before August 10th, 2024 are not available as they are under NDA

    def _clear_work_dir(self):
        # Clear the DepotDownloader's work directory, but not output directory

        work_dir = os.path.join(self.depot_downloader_output, '.DepotDownloader')
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)

            if self.verbose:
                print(f'Cleared {work_dir}')

    def run(self, manifest_id):
        current_game_version = load_game_info(os.path.join(self.output_dir, 'version.txt'))

        self._download(manifest_id)