
. ../../.env.local #Retrieve config paths

$DECOMPILER_PATH/Decompiler.exe -i "$DEADLOCK_PATH\game\citadel\pak01_dir.vpk" --output "decompiled-data" --vpk_filepath "scripts/heroes.vdata_c" -d
$DECOMPILER_PATH/Decompiler.exe -i "$DEADLOCK_PATH\game\citadel\pak01_dir.vpk" --output "decompiled-data" --vpk_filepath "scripts/abilities.vdata_c" -d
$DECOMPILER_PATH/Decompiler.exe -i "$DEADLOCK_PATH\game\citadel\pak01_dir.vpk" --output "decompiled-data" --vpk_filepath "scripts/generic_data.vdata_c" -d

mkdir -p "decompiled-data\localizations"
cp "$DEADLOCK_PATH\game\citadel\resource\localization\citadel_gc\citadel_gc_english.txt" "decompiled-data\localizations\citadel_gc_english.txt"
python3 parsers/localization.py "decompiled-data\localizations\citadel_gc_english.txt" "decompiled-data\localizations\citadel_gc_english.json"

cp "$DEADLOCK_PATH\game\citadel\resource\localization\citadel_mods\citadel_mods_english.txt" "decompiled-data\localizations\citadel_mods_english.txt"
python3 parsers/localization.py "decompiled-data\localizations\citadel_mods_english.txt" "decompiled-data\localizations\citadel_mods_english.json"

cp "$DEADLOCK_PATH\game\citadel\resource\localization\citadel_heroes\citadel_heroes_english.txt" "decompiled-data\localizations\citadel_heroes_english.txt"
python3 parsers/localization.py "decompiled-data\localizations\citadel_heroes_english.txt" "decompiled-data\localizations\citadel_heroes_english.json"
