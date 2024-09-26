import os
import kv3_to_json

DEADLOCK_PATH=os.getenv("DEADLOCK_PATH")
WORK_DIR=os.getenv("WORK_DIR")
OUTPUT_DIR=os.getenv("OUTPUT_DIR")

# Define paths
os.makedirs(WORK_DIR)
os.system('cp "$DEADLOCK_PATH/game/citadel/steam.inf" "$WORK_DIR/version.txt"')
os.system('cp "$DEADLOCK_PATH/game/citadel/steam.inf" "$OUTPUT_DIR/version.txt"')

# Define files to be decompiled and processed
files = [
  "scripts/heroes",
  "scripts/abilities",
  "scripts/generic_data",
  "scripts/misc"
]

os.makedirs(WORK_DIR+"/scripts")
# Loop through files and run Decompiler.exe for each
for file in files:
  input_path = DEADLOCK_PATH+"/game/citadel/pak01_dir.vpk" 
  VPK_FILEPATH = file + ".vdata_c"
  # Run the decompiler
  $DECOMPILER_CMD -i "$INPUT_PATH" --output "$WORK_DIR/vdata" --vpk_filepath "$VPK_FILEPATH" -d

  # Remove subclass and convert to json
  python3 kv3_to_json.py "$WORK_DIR/vdata/${FILE}.vdata" "$WORK_DIR/${FILE}.json"
done

# Define an array of folders to parse
#folders=("citadel_attributes" "citadel_dev" "citadel_gc" "citadel_generated_vo" "citadel_heroes" "citadel_main" "citadel_mods") # All folders
folders=("citadel_attributes" "citadel_gc" "citadel_heroes" "citadel_main" "citadel_mods") # All folders but voice lines and dev for now

# Loop through each folder in the array
for folder in "${folders[@]}"; do
    # Construct the source path using DEADLOCK_PATH and folder name
    src_path="$DEADLOCK_PATH/game/citadel/resource/localization/$folder"
    
    # Construct the destination path by replacing "citadel_" prefix with ""
    dest_folder_name="${folder#citadel_}"
    dest_path="$WORK_DIR/localizations/$dest_folder_name"
    mkdir -p $dest_path

    # Run the Python script to parse the folder
    python3 localization.py "$src_path" "$dest_path"
    echo "Parsed $src_path to $dest_path"
done