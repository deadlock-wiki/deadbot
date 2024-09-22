!#/bin/sh
if [ -f "../../../.env" ]; then
. ../../../.env #Retrieve config paths
fi
# Define paths
TMP_VDATA_DIR="decompiled-data/vdata"

if [ -f "$DECOMPILER_PATH/Decompiler.exe"  ]; then
  DEC_CMD="$DECOMPILER_PATH/Decompiler.exe"
  else
  DEC_CMD="$DECOMPILER_PATH/Decompiler"
fi
mkdir -p decompiled-data/scripts

cp "$DEADLOCK_PATH/game/citadel/steam.inf" "decompiled-data/version.txt"

# Define files to be decompiled and processed
FILES=("scripts/heroes" "scripts/abilities" "scripts/generic_data" "scripts/misc")
# Loop through files and run Decompiler.exe for each
for FILE in "${FILES[@]}"; do
  INPUT_PATH="$DEADLOCK_PATH/game/citadel/pak01_dir.vpk"
  VPK_FILEPATH="${FILE}.vdata_c"
  # Run the decompiler
  $DEC_CMD -i "$INPUT_PATH" --output "$TMP_VDATA_DIR" --vpk_filepath "$VPK_FILEPATH" -d

  # Remove subclass and convert to json
  VDATA_FILE="$TMP_VDATA_DIR/${FILE}.vdata"
  python3 kv3_to_json.py "$VDATA_FILE"
done

# Remove the vdata directory
rm -rf "$TMP_VDATA_DIR"


mkdir -p "decompiled-data/localizations"

# Define an array of folders to parse
#folders=("citadel_attributes" "citadel_dev" "citadel_gc" "citadel_generated_vo" "citadel_heroes" "citadel_main" "citadel_mods") # All folders
folders=("citadel_attributes" "citadel_gc" "citadel_heroes" "citadel_main" "citadel_mods") # All folders but voice lines and dev for now

# Loop through each folder in the array
for folder in "${folders[@]}"; do
    # Construct the source path using DEADLOCK_PATH and folder name
    src_path="$DEADLOCK_PATH/game/citadel/resource/localization/$folder"
    
    # Construct the destination path by replacing "citadel_" prefix with ""
    dest_folder_name="${folder#citadel_}"
    dest_path="decompiled-data/localizations/$dest_folder_name"
    mkdir -p $dest_path

    # Run the Python script to parse the folder
    python3 localization.py "$src_path" "$dest_path"
    echo "Parsed $src_path to $dest_path"
done