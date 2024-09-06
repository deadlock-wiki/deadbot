import sys
import json
import os

if __name__ == '__main__':
    # Arg1: Input folder which contains all localization files
    # Arg2: Output folder which all localization files will be placed in
    input_folder = sys.argv[1]
    output_folder = sys.argv[2]

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
                output_file_json = os.path.join(output_folder, filename.replace('.txt','.json'))
                #print(output_file_json)
                with open(output_file_json, 'w', encoding='utf-8') as f:
                    json.dump(out, f, indent=4)
        
