#! /bin/bash
# exit on error
set -e 

. .env # Retrieve env

cd src/parser/decompiler
if [ "$SKIP_DECOMPILER" = false ]; then
    echo "Decompiling source files..."
    bash decompile.sh
else
    echo "! Skipping Decompiler !"
fi

cd ../../..
if [ "$SKIP_PARSER" = false ]; then
    echo ""
    echo "Parsing decompiled files..."
    bash parser.sh
    echo ""
else
    echo "! Skipping Parser !"
fi

cd src
if [ "$SKIP_BOT" = "false" ]; then
    echo "Running DeadBot..."
    python3 deadbot.py
else
    echo "! Skipping DeadBot !"
fi


echo ""
echo "Done!"