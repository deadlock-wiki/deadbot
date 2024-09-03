#! /bin/bash
# exit on error
set -e 

cd src/parser
echo "Decompiling source files..."
bash decompile.sh

cd ../..
echo ""
echo "Parsing decompiled files..."
bash parser.sh
echo ""

cd src
echo "Running DeadBot..."
python3 deadbot.py

echo ""
echo "Done!"