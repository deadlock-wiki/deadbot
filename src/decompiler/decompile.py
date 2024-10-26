import os
import decompiler.kv3_to_json as kv3_to_json
import decompiler.localization as localization
import filecmp


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

    # Define paths
    os.makedirs(WORK_DIR, exist_ok=True)
    steam_inf_path = f'{DEADLOCK_PATH}/game/citadel/steam.inf'
    version_path = f'{WORK_DIR}/version.txt'

    # if the version files match, nothing to do
    if filecmp.cmp(steam_inf_path, version_path):
        print('version.txt and steam.inf have the same content.')
        if not force:
            return
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
    #   "citadel_mods"
    # ]

    # All folders but voice lines and dev for now
    folders = ['citadel_attributes', 'citadel_gc', 'citadel_heroes', 'citadel_main', 'citadel_mods']

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
        print(f'Parsed {src_path} to {dest_path}')
