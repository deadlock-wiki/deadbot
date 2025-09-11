import json
import os
import re
from loguru import logger


def process_files(input_folder, output_folder):
    """
    Parses Valve's KeyValue-like localization .txt files into JSON format.

    This function reads each .txt file, extracts key-value pairs, and performs
    specific string replacements for wiki compatibility (e.g., `\\n` to `<br>`).
    """
    # This regex finds the first "key" "value" pair on a line.
    # It's designed to be flexible, handling escaped quotes (`\"`) within the value
    # and ignoring surrounding text like comments or indentation.
    line_pattern = re.compile(r'"([^"]+)"\s*"((?:\\"|[^"])*)"')

    # Iterate all localizations in the input_folder
    for filename in os.listdir(input_folder):
        if filename.endswith('.txt'):
            file_path = os.path.join(input_folder, filename)

            with open(file_path, 'r', encoding='utf-8') as file:
                # remove new line chars after <br> and </li> to keep keys and values on same line
                text = file.read().replace('<br>\n', '').replace('</li>\n', '')

            lines = text.split('\n')
            out = dict()
            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    continue  # Skip empty lines

                # Use `search` to find the pattern anywhere in the string.
                match = line_pattern.search(stripped_line)
                if match:
                    left = match.group(1)
                    right = match.group(2).strip()

                    # Perform required replacements for wiki display.
                    right = right.replace('\\n', '<br>')
                    right = right.replace('\\"', '"')

                    out[left] = right
                else:
                    # Log lines that look like they should have matched, which could indicate a format change.
                    if '"' in stripped_line:
                        logger.debug(
                            f'Skipping malformed localization line in {filename}: '
                            f'"{stripped_line}"'
                        )

            output_file_json = os.path.join(output_folder, filename.replace('.txt', '.json'))
            # Ensure consistent Unix-style line endings.
            with open(output_file_json, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(out, f, ensure_ascii=False, indent=4)