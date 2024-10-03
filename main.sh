#! /bin/bash
# exit on error
set -e 

if [ -f ".env" ]; then
. .env # Retrieve env
fi

if [ "$DECOMPILE" = true ]; then
    cd src
    python3 deadbot.py --decompile=true --deadbot=false
    cd ..
fi

if [ "$PARSE" = true ]; then
    echo ""
    echo "Parsing decompiled files..."
    bash parser.sh
    echo ""
else
    echo "! Skipping Parser !"
fi

if [ "$BOT_PUSH" = true ]; then
    cd src
    python3 deadbot.py  # uses BOT_PUSH env var
    cd ..
fi

# cleanup
if [ "$CLEANUP" = true ]; then
    rm -rf $WORKDIR
fi


echo ""
echo "Done!"
