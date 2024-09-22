#! /bin/bash
# exit on error
set -e 

if [ -f ".env" ]; then
. .env # Retrieve env
fi

if [ "$SKIP_DECOMPILER" = false ]; then
    cd src/parser/decompiler
    echo "Decompiling source files..."
    bash decompile.sh
    cd ../../..
else
    echo "! Skipping Decompiler !"
fi

if [ "$SKIP_PARSER" = false ]; then
    echo ""
    echo "Parsing decompiled files..."
    bash parser.sh
    echo ""
else
    echo "! Skipping Parser !"
fi

if [ "$SKIP_BOT" = "false" ]; then
    cd src
    echo "Running DeadBot..."
    python3 deadbot.py
    cd ..
else
    echo "! Skipping DeadBot !"
fi

# cleanup
if [ "$OUTPUT_DIR/decompiled-data" ]; then
    rm -rf $OUTPUT_DIR/decompiled-data
fi


echo ""
echo "Done!"
