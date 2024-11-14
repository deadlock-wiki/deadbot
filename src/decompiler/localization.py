import json
import os


def process_files(input_folder, output_folder):
    # Iterate all localizations in the input_folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.txt'):
            file_path = os.path.join(input_folder, filename)

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                out = dict()
                for line in lines:
                    if line.count('"') >= 4:
                        left = line.split('"')[1]

                        # Handle cases where there are escaped quotations in the string
                        right = ''.join(line.split('"')[3:]).strip()
                        right = right.replace('\\', '"')

                        out[left] = right
                output_file_json = os.path.join(output_folder, filename.replace('.txt', '.json'))
                with open(output_file_json, 'w', encoding='utf-8') as f:
                    json.dump(out, f, ensure_ascii=False, indent=4)
