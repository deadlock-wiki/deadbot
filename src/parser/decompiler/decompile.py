import os
import kv3_to_json
from localization import process_localization_files

DEADLOCK_PATH=os.getenv("DEADLOCK_PATH")
WORK_DIR=os.getenv("WORK_DIR")
OUTPUT_DIR=os.getenv("OUTPUT_DIR")

# Define paths
os.makedirs(WORK_DIR)
os.system(f'cp "{DEADLOCK_PATH}/game/citadel/steam.inf" "{WORK_DIR}/version.txt"')
os.system(f'cp "{DEADLOCK_PATH}/game/citadel/steam.inf" "{OUTPUT_DIR}/version.txt"')

# Define files to be decompiled and processed
files = [
  "scripts/heroes",
  "scripts/abilities",
  "scripts/generic_data",
  "scripts/misc"
]

# Loop through files and run Decompiler.exe for each
for file in files:
  # removes filename from the file path
  folder_path = '/'.join(str.split(file,'/')[:-1])
  os.makedirs(WORK_DIR+"/"+folder_path)

  input_path = DEADLOCK_PATH+"/game/citadel/pak01_dir.vpk" 
  VPK_FILEPATH = file + ".vdata_c"
  # Run the decompiler
  dec_cmd = f'{DECOMPILER_CMD} -i "{INPUT_PATH}" --output "{WORK_DIR}/vdata" --vpk_filepath "{VPK_FILEPATH}" -d'
  os.system(dec_cmd)
  # Remove subclass and convert to json
  kv3_to_json.process_file(f"{WORK_DIR}/vdata/{FILE}.vdata", f"{WORK_DIR}/{FILE}.json")

# Define an array of folders to parse
#folders=("citadel_attributes" "citadel_dev" "citadel_gc" "citadel_generated_vo" "citadel_heroes" "citadel_main" "citadel_mods") # All folders
# All folders but voice lines and dev for now
folders = [
  "citadel_attributes",
  "citadel_gc",
  "citadel_heroes",
  "citadel_main",
  "citadel_mods"
]

# Loop through each folder in the array
for folder in folders:
    # Construct the source path using DEADLOCK_PATH and folder name
    src_path = f"{DEADLOCK_PATH}/game/citadel/resource/localization/{folder}"
    
    # Construct the destination path by replacing "citadel_" prefix with ""
    dest_folder_name = str.replace(folder,"citadel_","")
    dest_path = f"{WORK_DIR}/localizations/{dest_folder_name}"
    os.makedirs(dest_path)

    # Run the Python script to parse the folder
    process_localization_files(src_path,dest_path)
    print(f"Parsed {src_path} to {dest_path}")