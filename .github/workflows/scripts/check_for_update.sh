#!/usr/bin/env bash

# Compares the Deadlock client versions between deadlock-data master and the latest on steamdb
# If steamdb has a later version available, it outputs the new version number

# local repository paths for steamdb and deadlock-data
STEAMDB=$1
DEADLOCK_DATA=$2

# Read the file and extract ClientVersion
latest_inf_file="${STEAMDB}/game/citadel/steam.inf"
if [[ -f "$latest_inf_file" ]]; then
    client_version=$(grep '^ClientVersion=' "$latest_inf_file" | cut -d'=' -f2)
else
    echo "Error: steam.inf file not found at $latest_inf_file" >&2
    exit 1
fi

# same thing for deadlock data
deployed_inf_file="${DEADLOCK_DATA}/data/version.txt"
if [[ -f "$deployed_inf_file" ]]; then
    client_version=$(grep '^ClientVersion=' "$deployed_inf_file" | cut -d'=' -f2)
else
    echo "Error: version.txt file not found at $deployed_inf_file" >&2
    exit 1
fi

latest_version=$(grep '^ClientVersion=' $latest_inf_file | cut -d'=' -f2)
deployed_version=$(grep '^ClientVersion=' $deployed_inf_file | cut -d'=' -f2)   

if [[ -z "$latest_version" ]]; then
    echo "Error: Latest version not found in $latest_inf_file" >&2
    exit 1
fi

if [[ -z "$deployed_version" ]]; then
    echo "Error: Deployed version not found in $deployed_inf_file" >&2
    exit 1
fi

if [[ "$latest_version" == "$deployed_version" ]]; then
    echo ""
    exit 0
else
    echo $latest_version
    exit 0
fi
