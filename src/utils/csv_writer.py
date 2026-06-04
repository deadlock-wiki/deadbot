import csv
import json
import os


def export_json_file_to_csv(file_name, OUTPUT_DIR):
    os.makedirs(f'{OUTPUT_DIR}/json', exist_ok=True)
    with open(f'{OUTPUT_DIR}/json/{file_name}.json') as f:
        data = json.load(f)

    os.makedirs(f'{OUTPUT_DIR}/csv', exist_ok=True)
    if data:
        all_keys = dict.fromkeys(k for row in data.values() for k in row.keys())
        fieldnames = [''] + list(all_keys)
        with open(f'{OUTPUT_DIR}/csv/{file_name}.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row_key, row in data.items():
                writer.writerow({'': row_key, **{k: convert_array_to_string(v) for k, v in row.items()}})


def convert_array_to_string(value):
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)
    return value
