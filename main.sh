#! /bin/bash
# exit on error
set -e 

cd src/parser
echo "Decompiling source files..."
bash decompile.sh

echo ""
echo "Parsing decompiled files..."
python3 parser.py

cd ..
echo "Running DeadBot..."
python3 deadbot.py

echo ""
echo "Done! exported data to 'output/'"