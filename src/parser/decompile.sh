
. ../../.env.local #Retrieve config paths

$DECOMPILER_PATH/Decompiler.exe -i "$DEADLOCK_PATH\game\citadel\pak01_dir.vpk" --output "decompiled-data/vdata" --vpk_filepath "scripts/heroes.vdata_c" -d
$DECOMPILER_PATH/Decompiler.exe -i "$DEADLOCK_PATH\game\citadel\pak01_dir.vpk" --output "decompiled-data/vdata" --vpk_filepath "scripts/abilities.vdata_c" -d
$DECOMPILER_PATH/Decompiler.exe -i "$DEADLOCK_PATH\game\citadel\pak01_dir.vpk" --output "decompiled-data/vdata" --vpk_filepath "scripts/generic_data.vdata_c" -d

mkdir -p "decompiled-data\json\localizations"

# Define an array of folders to parse
#folders=("citadel_attributes" "citadel_dev" "citadel_gc" "citadel_generated_vo" "citadel_heroes" "citadel_main" "citadel_mods") # All folders
folders=("citadel_attributes" "citadel_gc" "citadel_heroes" "citadel_main" "citadel_mods") # All folders but voice lines and dev for now

# Loop through each folder in the array
for folder in "${folders[@]}"; do
  # Construct the source path using DEADLOCK_PATH and folder name
  src_path="$DEADLOCK_PATH/game/citadel/resource/localization/$folder"
  
  # Construct the destination path by replacing "citadel_" prefix with ""
  dest_folder_name="${folder#citadel_}"
  dest_path="decompiled-data/json/localizations/$dest_folder_name"
  mkdir -p $dest_path

  # Run the Python script to parse the folder
  python3 parsers/localization.py "$src_path" "$dest_path"
  echo "Parsed $src_path to $dest_path"
done