#!/usr/bin/env bash
set -e

FILE="pyproject.toml"
BRANCH="${GITHUB_HEAD_REF#refs/heads/}"
# lowercase branch for matching
BRANCH_NAME=${BRANCH,,}

git fetch origin master

MASTER_VERSION=$(git show origin/master:$FILE | grep -Po '(?<=version = ")[0-9]+\.[0-9]+\.[0-9]+')
IFS='.' read -r MJR MNR PCH <<< "$MASTER_VERSION"

# Release/vX.Y.Z branch directly sets the new version
if [[ "$BRANCH_NAME" =~ ^release\/v([0-9]+\.[0-9]+\.[0-9]+) ]]; then
  NEW_VERSION="${BASH_REMATCH[1]}"

# hotfix/* branch increments fix version
elif [[ "$BRANCH_NAME" =~ ^hotfix\/ ]]; then
  PCH=$((PCH + 1))
  NEW_VERSION="$MJR.$MNR.$PCH"

# throw error if correct branching is not used
else
  echo "Branch must match 'release/vX.Y.Z' or 'hotfix/*'"
  exit 1
fi

CURRENT_VERSION=$(grep -Po '(?<=version = ")[0-9]+\.[0-9]+\.[0-9]+' "$FILE")
if [[ "$CURRENT_VERSION" == "$NEW_VERSION" ]]; then
  echo "Version already updated. Skipping."
  exit 0
fi

echo "Updating version from $MASTER_VERSION to $NEW_VERSION"

sed -i -E "s/version = \"[0-9]+\.[0-9]+\.[0-9]+\"/version = \"$NEW_VERSION\"/" "$FILE"

git config user.email "deadbot1101@gmail.com"
git config user.name "Deadbot0"

git add pyproject.toml
git commit -m "[skip ci] chore: bumped version to $NEW_VERSION" || echo "No changes to commit"
git push --force-with-lease origin "$GITHUB_REF"
