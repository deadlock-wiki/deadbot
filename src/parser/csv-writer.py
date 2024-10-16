import pandas as pd
import os

OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../output-data')


def export_json_file_to_csv(file_name):
    os.makedirs(f'{OUTPUT_DIR}/json', exist_ok=True)
    df = pd.read_json(f'{OUTPUT_DIR}/json/{file_name}.json').transpose()
    df = df.applymap(convert_array_to_string)
    os.makedirs(f'{OUTPUT_DIR}/csv', exist_ok=True)
    df.to_csv(f'{OUTPUT_DIR}/csv/{file_name}.csv')


def convert_array_to_string(value):
    if isinstance(value, list):
        return ', '.join(str(value))
    return value


if __name__ == '__main__':
    export_json_file_to_csv('item-data')
    export_json_file_to_csv('hero-data')
