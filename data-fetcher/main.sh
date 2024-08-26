#! /bin/bash
# exit on error
set -e 

bash decompile.sh
python3 parser.py

echo ""
echo "Done! exported data to 'output/'"