import os
import shutil
from loguru import logger
from utils.process import run_process
from .constants import APP_ID, DEPOT_ID


class DepotDownloader:
    def __init__(self, output_dir, depot_downloader_cmd_dir, steam_username, steam_password, verbose=True):
        if not depot_downloader_cmd_dir:
            raise Exception('Config for DepotDownloader path is required')
        if not os.path.exists(depot_downloader_cmd_dir):
            raise Exception(f'Could not find DepotDownloader at path "{depot_downloader_cmd_dir}"')
        self.depot_downloader_cmd_dir = depot_downloader_cmd_dir

        self.app_id = APP_ID  # deadlock's app_id
        self.depot_id = DEPOT_ID  # the big depot

        self.output_dir = output_dir
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.depot_downloader_output = './game-data/'
        self.manifest_path = os.path.join(self.depot_downloader_output, 'manifest.txt')

    def run(self, manifest_id):
        # Check if the manifest is already downloaded
        downloaded_manifest_id = self._read_downloaded_manifest_id()
        if downloaded_manifest_id == manifest_id:
            logger.trace(f'Already downloaded manifest {manifest_id}')
            return

        self._clear_dl_data()
        self._download(manifest_id)
        self._write_downloaded_manifest_id(manifest_id)

    def _download(self, manifest_id):
        # Run the depot_downloader command
        subprocess_params = [
            os.path.join(self.depot_downloader_cmd_dir),
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
        run_process(subprocess_params, name='DepotDownloader')

        steam_inf_path = os.path.join(self.depot_downloader_output, 'game', 'citadel', 'steam.inf')
        if not os.path.exists(steam_inf_path):
            raise Exception(f'Fatal error: {steam_inf_path} not found')

    def _clear_dl_data(self):
        """Clear downloaded data, but not the manifest.txt"""
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
