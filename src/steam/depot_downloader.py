import os
import shutil
from loguru import logger
from utils.process import run_process

APP_ID = '1422450'  # deadlock's app_id
DEPOT_ID = '1422456'  # the big depot


class DepotDownloader:
    def __init__(self, output_dir, deadlock_dir, depot_downloader_cmd, steam_username, steam_password, force):
        if not depot_downloader_cmd:
            raise Exception('Config for DepotDownloader path is required')
        if not os.path.exists(depot_downloader_cmd):
            raise Exception(f'Could not find DepotDownloader at path "{depot_downloader_cmd}"')
        if not steam_username or not steam_password:
            raise Exception('Steam username and password are required')

        self.depot_downloader_cmd = depot_downloader_cmd

        self.app_id = APP_ID
        self.depot_id = DEPOT_ID

        self.output_dir = output_dir
        self.steam_username = steam_username
        self.steam_password = steam_password
        self.deadlock_dir = deadlock_dir
        self.manifest_path = os.path.join(self.deadlock_dir, 'manifest.txt')
        self.force = force

    def download_files(self, files: list[str] = None, file_list_path: str = None, manifest_id: str = None, logger_name: str = 'download-files'):
        """
        Download a list of files from the configured depot. If `manifest_id` is None, the latest manifest will be referenced.
        If `files` and `file_list_path` are both provided, the final file list will be the combination of both.
        Args:
            files (list[str]): List of game files
            file_list_path (str): Path to a file containing a list of game files to download
            manifest_id (str): ID of the manifest to download files from. If None, the latest manifest will be used.
            logger_name (str): Name of the logger to use for logging. Defaults to 'download-files'.
        """
        if files is None and file_list_path is None:
            raise ValueError('At least one of files or file_list_path must be provided')

        combined_file_list_path = os.path.join(self.deadlock_dir, 'files_to_download.txt')

        try:
            # Clear the old file list if it exists
            os.remove(combined_file_list_path)
        except FileNotFoundError:
            pass

        # Do not handle exceptions here, if a file is not found, can't be opened, etc. we should crash
        if file_list_path is not None:
            shutil.copy(file_list_path, combined_file_list_path)

        # Append the passed list of files to the file list
        if files is not None:
            with open(combined_file_list_path, 'a', encoding='utf-8') as file_list:
                file_list.write('\n'.join(files))

        subprocess_params = [
            os.path.join(self.depot_downloader_cmd),
            '-app',
            self.app_id,
            '-depot',
            self.depot_id,
            '-username',
            self.steam_username,
            '-password',
            self.steam_password,
            '-remember-password',
            '-filelist',
            combined_file_list_path,
            '-dir',
            self.deadlock_dir,
        ]
        if manifest_id is not None:
            subprocess_params.extend(['-manifest', manifest_id])

        run_process(subprocess_params, name=logger_name)

    def _download(self, manifest_id):
        logger.trace(f'Downloading game with manifest id {manifest_id}')

        file_list_path = os.path.join(os.path.dirname(__file__), 'depot_downloader_file_list.txt')

        subprocess_params = [
            os.path.join(self.depot_downloader_cmd),
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
            file_list_path,
            '-dir',
            self.deadlock_dir,
        ]
        run_process(subprocess_params, name='download-game-files')

        steam_inf_path = os.path.join(self.deadlock_dir, 'game', 'citadel', 'steam.inf')
        if not os.path.exists(steam_inf_path):
            raise Exception(f'Fatal error: {steam_inf_path} not found')

    def _read_downloaded_manifest_id(self):
        if not os.path.exists(self.manifest_path):
            return None

        with open(self.manifest_path, 'r') as f:
            return f.read().strip()

    def _get_latest_manifest_id(self):
        # create temporary folder to store manifest file
        temp_dir = os.path.join(self.deadlock_dir, 'temp')

        subprocess_params = [
            os.path.join(self.depot_downloader_cmd),
            '-app',
            self.app_id,
            '-depot',
            self.depot_id,
            '-username',
            self.steam_username,
            '-password',
            self.steam_password,
            '-remember-password',
            '-dir',
            temp_dir,
            '-manifest-only',
            '-validate',
        ]
        run_process(subprocess_params, name='get-latest-manifest-id')

        manifest_id = None
        for filename in os.listdir(temp_dir):
            if filename.startswith('manifest'):
                # manifest formatted as manifest_<depot_id>_<manifest_id>.txt
                manifest_id = filename.replace('manifest_', '').replace('.txt', '').split('_')[-1]

        shutil.rmtree(temp_dir)
        return manifest_id

    def _write_downloaded_manifest_id(self, manifest_id):
        print('Writing manifest id', manifest_id, 'to', self.manifest_path)
        with open(self.manifest_path, 'w') as f:
            f.write(manifest_id)
