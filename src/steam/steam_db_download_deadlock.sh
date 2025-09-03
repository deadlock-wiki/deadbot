#!/bin/bash
GAME_DIR=$DEADLOCK_DIR

if [ -z "$GAME_DIR" ]; then
    echo "Error: GAME_DIR is required"
    exit 1
fi

# if the working directory is a git repo, pull the latest changes, otherwise clone the repo#
if [ -d "$GAME_DIR/.git" ]; then
    echo "Updating existing GameTracking-Deadlock repository in $GAME_DIR"
    cd $GAME_DIR
    git stash
    git pull
    cd ..
else
    echo "Cloning GameTracking-Deadlock repository into $GAME_DIR"
    git clone https://github.com/SteamDatabase/GameTracking-Deadlock.git $GAME_DIR
fi

exit 0
