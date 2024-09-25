#! /bin/bash
# exit on error
set -e 

if [ -f ".env" ]; then
. .env # Retrieve env
fi

if [ "$DECOMPILE" = true ]; then
    cd src/parser/decompiler
    echo "Decompiling source files..."
    bash decompile.sh
    cd ../../..
else
    echo "! Skipping Decompiler !"
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
    echo "Running DeadBot..."
    python3 deadbot.py
    cd ..
else
    echo "! Skipping DeadBot !"
fi

# cleanup
if [ "$CLEANUP" = true ]; then
    rm -rf $WORKDIR
fi


echo ""
echo "Done!"
