#!/usr/bin/env bash
set -e

FILE="pyproject.toml"
BRANCH="$BRANCH_NAME"

git fetch origin master

MASTER_VERSION=$(git show origin/master:$FILE | grep -Po '(?<=version = ")[0-9]+\.[0-9]+\.[0-9]+')
IFS='.' read -r MJR MNR PCH <<< "$MASTER_VERSION"

# lowercase branch for matching
BRANCH_LOWER=${BRANCH,,}

# Release/vX.Y.Z branch directly sets the new version
if [[ "$BRANCH_LOWER" =~ ^release/v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  NEW_VERSION="${BASH_REMATCH[1]}"

# hotfix/* branch increments fix version
elif [[ "$BRANCH_LOWER" == hotfix/* ]]; then
  PCH=$((PCH + 1))
  NEW_VERSION="$MJR.$MNR.$PCH"

# throw error if correct branching is not used
else
  echo "Branch must match 'Release/vX.Y.Z' or 'hotfix/*'"
  exit 1
fi

CURRENT_VERSION=$(grep -Po '(?<=version = ")[0-9]+\.[0-9]+\.[0-9]+' "$FILE")
if [[ "$CURRENT_VERSION" == "$NEW_VERSION" ]]; then
  echo "Version already updated. Skipping."
  exit 0
fi

echo "Updating version from $MASTER_VERSION to $NEW_VERSION"

sed -i -E "s/version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$NEW_VERSION\"/" "$FILE"

git config --global user.email "deadbot1101@gmail.com"
git config --global user.name "Deadbot0"
git add pyproject.toml
git commit -m "[skip ci] chore: bumped version to v$NEW_VERSION" || echo "No changes to commit"
