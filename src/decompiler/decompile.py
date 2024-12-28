import os
import decompiler.kv3_to_json as kv3_to_json
import decompiler.localization as localization
import filecmp
import shutil
import utils.game_utils as g_util
from loguru import logger


def decompile(DEADLOCK_PATH, WORK_DIR, DECOMPILER_CMD, force=False):
    """
    Decompiles deadlock game files and generated parsed output.

    Args:
        DEADLOCK_PATH (str): The path to the deadlock game files.
        WORK_DIR (str): The working directory for the decompilation process.
        DECOMPILER_CMD (str): The command used to run the decompiler.
        force (bool): If true, will decompile files even if the version already exists

    Returns:
        None
    """
    os.makedirs(WORK_DIR, exist_ok=True)
    steam_inf_path = f'{DEADLOCK_PATH}/game/citadel/steam.inf'
    version_path = f'{WORK_DIR}/version.txt'

    # if the version files match, nothing to do
    if os.path.exists(version_path) and filecmp.cmp(steam_inf_path, version_path):
        game_version = g_util.load_game_info(steam_inf_path)
        if not force:
            logger.info(
                f'Version {game_version["ClientVersion"]} is '
                + 'already decompiled, skipping decompile step'
            )
            return

    # clear data to ensure no old data is left around
    shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR, exist_ok=True)

    os.system(f'cp "{steam_inf_path}" "{version_path}"')

    # Define files to be decompiled and processed
    files = ['scripts/heroes', 'scripts/abilities', 'scripts/generic_data', 'scripts/misc']

    # Loop through files and run Decompiler.exe for each
    for file in files:
        # removes filename from the file path
        folder_path = '/'.join(str.split(file, '/')[:-1])
        os.makedirs(WORK_DIR + '/' + folder_path, exist_ok=True)

        input_path = DEADLOCK_PATH + '/game/citadel/pak01_dir.vpk'
        VPK_FILEPATH = file + '.vdata_c'
        # Run the decompiler
        dec_cmd = (
            DECOMPILER_CMD
            + f' -i "{input_path}" --output "{WORK_DIR}/vdata" --vpk_filepath "{VPK_FILEPATH}" -d'
        )

        os.system(dec_cmd)

        # Ensure the vdata directory was created successfully
        if not os.path.exists(f'{WORK_DIR}/vdata'):
            raise Exception(f'Fatal error: Failed to decompile {input_path} with {VPK_FILEPATH}')

        # Remove subclass and convert to json
        kv3_to_json.process_file(f'{WORK_DIR}/vdata/{file}.vdata', f'{WORK_DIR}/{file}.json')

    # Define an array of folders to parse
    # All folders (UNUSED)
    # all_folders = [
    #   "citadel_attributes",
    #   "citadel_dev",
    #   "citadel_gc",
    #   "citadel_generated_vo",
    #   "citadel_heroes",
    #   "citadel_main",
    #   "citadel_mods",
    #   "citadel_patch_notes",
    # ]

    # All folders but voice lines and dev for now
    folders = [
        'citadel_attributes',
        'citadel_gc',
        'citadel_heroes',
        'citadel_main',
        'citadel_mods',
        'citadel_patch_notes',
    ]

    # Loop through each folder in the array
    for folder in folders:
        # Construct the source path using DEADLOCK_PATH and folder name
        src_path = f'{DEADLOCK_PATH}/game/citadel/resource/localization/{folder}'

        # Construct the destination path by replacing "citadel_" prefix with ""
        dest_folder_name = str.replace(folder, 'citadel_', '')
        dest_path = f'{WORK_DIR}/localizations/{dest_folder_name}'
        os.makedirs(dest_path, exist_ok=True)

        # Run the Python script to parse the folder
        localization.process_files(src_path, dest_path)
        logger.trace(f'Parsed {src_path} to {dest_path}')
