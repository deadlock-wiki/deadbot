#!/usr/bin/env bash

# Compares the Deadlock client versions between deadlock-data master and the latest on steamdb
# If steamdb has a later version available, it outputs the new version number

# local repository paths for steamdb and deadlock-data
STEAMDB=$1
DEADLOCK_DATA=$2

latest_file=$STEAMDB/game/citadel/steam.inf
deployed_file=$DEADLOCK_DATA/data/version.txt

# --- existence checks ---
[[ -f $latest_file ]]   || { echo "Error: $latest_file not found" >&2;   exit 1; }
[[ -f $deployed_file ]] || { echo "Error: $deployed_file not found" >&2; exit 1; }

# --- extract versions ---
latest_version=$(grep -m1 '^ClientVersion=' "$latest_file"   | cut -d= -f2 | tr -d '\r')
deployed_version=$(grep -m1 '^ClientVersion=' "$deployed_file" | cut -d= -f2 | tr -d '\r')

# --- non-empty checks ---
[[ -n $latest_version ]]   || { echo "Error: no ClientVersion in $latest_file" >&2;   exit 1; }
[[ -n $deployed_version ]] || { echo "Error: no ClientVersion in $deployed_file" >&2; exit 1; }

# --- compare and output new version if different ---
if [[ $latest_version != "$deployed_version" ]]; then
    echo "$latest_version"
fi
