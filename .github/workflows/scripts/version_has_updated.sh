#!/usr/bin/env bash
set -euo pipefail

# Get current branch version
current_version=$(grep -E '^version\s*=' pyproject.toml | sed -E 's/version\s*=\s*"([^"]+)"/\1/')
# Strip -beta.x if present
current_base=$(echo "$current_version" | sed -E 's/-beta\.[0-9]+//')

# Get master branch version (without switching branches)
master_version=$(git show master:pyproject.toml | grep -E '^version\s*=' | sed -E 's/version\s*=\s*"([^"]+)"/\1/')
master_base=$(echo "$master_version" | sed -E 's/-beta\.[0-9]+//')

echo "Current branch version: $current_version (base: $current_base)"
echo "Master branch version:  $master_version (base: $master_base)"

if [[ "$current_base" == "$master_base" ]]; then
  echo "❌ Version has not changed, please update pyproject.toml version."
  exit 1
else
  echo "✅ Version changed."
  exit 0
fi
