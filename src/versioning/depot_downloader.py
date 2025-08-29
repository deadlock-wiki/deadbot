import subprocess
import os
from loguru import logger
import shutil
from constants import APP_ID, DEPOT_ID


class DepotDownloader:
    def __init__(
        self, output_dir, depot_downloader_cmd_dir, steam_username, steam_password, verbose=True
    ):
        self.app_id = APP_ID  # deadlock's app_id
        self.depot_id = DEPOT_ID  # the big depot

        self.output_dir = output_dir
        self.depot_downloader_cmd_dir = depot_downloader_cmd_dir
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.depot_downloader_output = 'deadlock-data'
        self.manifest_path = os.path.join(self.depot_downloader_output, 'manifest.txt')

    def _download(self, manifest_id):
        result = None
        try:
            # Run the depot_downloader command
            subprocess_params = [
                os.path.join(self.depot_downloader_cmd_dir, './DepotDownloader'),
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
            logger.debug('DepotDownloader output: ' + result.stdout)
            if not os.path.exists(steam_inf_path):
                raise Exception(f'Fatal error: {steam_inf_path} not found')

        except Exception as e:
            # if result is not None:
            # print('DepotDownloader output: ' + result.stdout)
            raise Exception(f'Error occured while parsing manifest {manifest_id}, error: {e}')
            # Possible errors that cause exceptions include:
            # RateLimiting by Steam
            # Manifest download being blocked by developers
            # Manifests before August 10th, 2024 are not available as they are under NDA

    def _clear_dl_data(self):
        # Clear downloaded data, but not the manifest.txt
        dirs = ['.DepotDownloader', 'game']
        for dir in dirs:
            dir_to_rm = os.path.join(self.depot_downloader_output, dir)
            if os.path.exists(dir_to_rm):
                shutil.rmtree(dir_to_rm)
                logger.trace(f'Cleared {dir_to_rm}')

    def _read_downloaded_manifest_id(self):
        if not os.path.exists(self.manifest_path):
            return None

        with open(self.manifest_path, 'r') as f:
            return f.read().strip()

    def _write_downloaded_manifest_id(self, manifest_id):
        with open(self.manifest_path, 'w') as f:
            f.write(manifest_id)

    def run(self, manifest_id):
        # Check if the manifest is already downloaded
        downloaded_manifest_id = self._read_downloaded_manifest_id()
        if downloaded_manifest_id == manifest_id:
            logger.trace(f'Already downloaded manifest {manifest_id}')
            return

        # Clear the existing data
        self._clear_dl_data()

        # Download the manifest
        self._download(manifest_id)

        # Write the downloaded manifest id
        self._write_downloaded_manifest_id(manifest_id)
