import os
import shutil
import decompiler.kv3_to_json as kv3_to_json
import decompiler.localization as localization
import filecmp
import utils.game_utils as g_util
from loguru import logger


class Decompiler:
    """Handles all of the raw game data downloading and decompiling

    Args:
        deadlock_dir (str): The path to the deadlock game files.
        work_dir (str): The working directory for the decompilation process.
        force (bool): If true, will decompile files even if the version already exists
    """

    def __init__(self, deadlock_dir, work_dir, force=False):
        self.deadlock_dir = deadlock_dir
        self.work_dir = work_dir
        self.force = force

    def run(self):
        steam_inf_path = f'{self.deadlock_dir}/game/citadel/steam.inf'
        version_path = f'{self.work_dir}/version.txt'

        # if the version files match, nothing to do
        if os.path.exists(version_path) and filecmp.cmp(steam_inf_path, version_path):
            game_version = g_util.load_game_info(steam_inf_path)
            if not self.force:
                logger.info(f'Version {game_version["ClientVersion"]} is already decompiled, skipping decompile step')
                return

        shutil.rmtree(self.work_dir, ignore_errors=True)
        self._import_game_data()
        self._import_localization_data()

        # Save version information to prevent unnecessary future decompiles
        os.system(f'cp "{steam_inf_path}" "{version_path}"')

    def _import_game_data(self):
        """
        Download bulk of the game data from https://github.com/SteamDatabase/GameTracking-Deadlock.git and convert to json

        Args:
            deadlock_dir (str): The path to the deadlock game files.
            work_dir (str): The working directory for the decompilation process.
            force (bool): If true, will decompile files even if the version already exists

        Returns:
            None
        """
        # map of file names to read from deadlock dir to an output path in work dir
        GAMEFILE_TO_WORK_DIR = {
            'game/citadel/pak01_dir/scripts/heroes': 'scripts/heroes',
            'game/citadel/pak01_dir/scripts/abilities': 'scripts/abilities',
            'game/citadel/pak01_dir/scripts/generic_data': 'scripts/generic_data',
            'game/citadel/pak01_dir/scripts/misc': 'scripts/misc',
            'game/citadel/pak01_dir/scripts/npc_units': 'scripts/npc_units',
        }

        os.makedirs(self.work_dir, exist_ok=True)

        for gamefile, workfile in GAMEFILE_TO_WORK_DIR.items():
            # Remove subclass and convert to json
            kv3_to_json.process_file(f'{self.deadlock_dir}/{gamefile}.vdata', f'{self.work_dir}/{workfile}.json')

    def _import_localization_data(self):
        # All folders but voice lines and dev for now
        LOCALIZATION_FOLDERS = [
            'citadel_attributes',
            'citadel_gc',
            'citadel_gc_hero_names',
            'citadel_gc_mod_names',
            'citadel_heroes',
            'citadel_main',
            'citadel_mods',
            'citadel_patch_notes',
        ]

        # Loop through each folder in the array
        for folder in LOCALIZATION_FOLDERS:
            # Construct the source path using deadlock_dir and folder name
            src_path = f'{self.deadlock_dir}/game/citadel/resource/localization/{folder}'

            # Construct the destination path by replacing "citadel_" prefix with ""
            dest_folder_name = str.replace(folder, 'citadel_', '')
            dest_path = f'{self.work_dir}/localizations/{dest_folder_name}'
            os.makedirs(dest_path, exist_ok=True)

            # Run the Python script to parse the folder
            localization.process_files(src_path, dest_path)
            logger.trace(f'Parsed {src_path} to {dest_path}')
