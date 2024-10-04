#! /bin/bash
# exit on error
set -e 

if [ -f ".env" ]; then
. .env # Retrieve env
fi

python3 src/deadbot.py

# cleanup
if [ "$CLEANUP" = true ]; then
    rm -r $WORKDIR
fi
