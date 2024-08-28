
# DEADLOCK_LOCATION="D:\SteamLibrary\steamapps\common\Deadlock"
DEADLOCK_LOCATION="C:\Program Files (x86)\Steam\steamapps\common\Deadlock"

DECOMPILER_LOCATION=~/Downloads/Decompiler-windows-x64

$DECOMPILER_LOCATION/Decompiler.exe -i "$DEADLOCK_LOCATION\game\citadel\pak01_dir.vpk" --output "decompiled-data" --vpk_filepath "scripts/heroes.vdata_c" -d
$DECOMPILER_LOCATION/Decompiler.exe -i "$DEADLOCK_LOCATION\game\citadel\pak01_dir.vpk" --output "decompiled-data" --vpk_filepath "scripts/abilities.vdata_c" -d
$DECOMPILER_LOCATION/Decompiler.exe -i "$DEADLOCK_LOCATION\game\citadel\pak01_dir.vpk" --output "decompiled-data" --vpk_filepath "scripts/generic_data.vdata_c" -d

mkdir -p "decompiled-data\localizations"
cp "$DEADLOCK_LOCATION\game\citadel\resource\localization\citadel_gc\citadel_gc_english.txt" "decompiled-data\localizations\citadel_gc_english.txt"
python3 localization_parser.py "decompiled-data\localizations\citadel_gc_english.txt" "decompiled-data\localizations\citadel_gc_english.json"

cp "$DEADLOCK_LOCATION\game\citadel\resource\localization\citadel_mods\citadel_mods_english.txt" "decompiled-data\localizations\citadel_mods_english.txt"
python3 localization_parser.py "decompiled-data\localizations\citadel_mods_english.txt" "decompiled-data\localizations\citadel_mods_english.json"