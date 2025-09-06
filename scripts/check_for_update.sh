STEAMDB='../game-data'
DEADLOCK_DATA='../../deadlock-data/data'

# Read the file and extract ClientVersion
latest_inf_file="${STEAMDB}/game/citadel/steam.inf"
if [[ -f "$latest_inf_file" ]]; then
    client_version=$(grep '^ClientVersion=' "$latest_inf_file" | cut -d'=' -f2)
else
    echo "steam.inf file not found at $latest_inf_file"
    exit 1
fi

# same thing for deadlock data
deployed_inf_file="${DEADLOCK_DATA}/version.txt"
if [[ -f "$deployed_inf_file" ]]; then
    client_version=$(grep '^ClientVersion=' "$deployed_inf_file" | cut -d'=' -f2)
else
    echo "version.txt file not found at $deployed_inf_file"
    exit 1
fi

latest_version=$(grep '^ClientVersion=' $latest_inf_file | cut -d'=' -f2)
deployed_version=$(grep '^ClientVersion=' $deployed_inf_file | cut -d'=' -f2)   

if [[ "$latest_version" == "$deployed_version" ]]; then
    echo $latest_version
    exit 0
else
    exit 0
fi
