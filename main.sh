#! /bin/bash
# exit on error
set -e 

if [ -f ".env" ]; then
. .env # Retrieve env
fi

# Configured completly from env vars:
poetry run deadbot

# cleanup
if [ "$CLEANUP" = true ]; then
    rm -r $WORKDIR
fi
