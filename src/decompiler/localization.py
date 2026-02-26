import json
import os
import re


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
                    raw_right = match.group(2)

                    # Perform a series of safe, ordered replacements to handle C-style escapes
                    # without corrupting Unicode characters.
                    # 1. Handle escaped backslashes first to prevent them from interfering.
                    # 2. Handle escaped quotes and newlines.
                    unescaped_right = raw_right.replace('\\\\', '\\')
                    unescaped_right = unescaped_right.replace('\\"', '"')
                    unescaped_right = unescaped_right.replace("\\'", "'")
                    unescaped_right = unescaped_right.replace('\\n', '\n')

                    # Now that the string is properly un-escaped, we can safely replace the
                    # literal newline characters with <br> tags for the wiki.
                    right = unescaped_right.replace('\n', '<br>').strip()

                    # Strip Valve gender markers (e.g., #|m|#, #|f|#) from values
                    right = re.sub(r'#\|[mf]\|#', '', right)

                    out[left] = right

            output_file_json = os.path.join(output_folder, filename.replace('.txt', '.json'))
            # Ensure consistent Unix-style line endings.
            with open(output_file_json, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(out, f, ensure_ascii=False, indent=4)
