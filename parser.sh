#! /bin/bash
cd src/parser
python3 parser.py

echo "Exporting to CSV..."
python3 csv-writer.py
