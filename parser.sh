#! /bin/bash
cd src/parser
python3 parser.py

echo "Exporting to CSV..."
cd ..
python3 csv-writer.py
