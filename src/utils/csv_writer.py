import pandas as pd
import os
import json


def export_json_file_to_csv(file_name, OUTPUT_DIR):
    os.makedirs(f'{OUTPUT_DIR}/json', exist_ok=True)
    df = pd.read_json(f'{OUTPUT_DIR}/json/{file_name}.json').transpose()
    df = df.map(convert_value)
    os.makedirs(f'{OUTPUT_DIR}/csv', exist_ok=True)
    df.to_csv(f'{OUTPUT_DIR}/csv/{file_name}.csv')


def convert_value(value):
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value)
    return value