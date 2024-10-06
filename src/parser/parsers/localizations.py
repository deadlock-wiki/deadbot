import os

import utils.json_utils as json_utils


class LocalizationParser:
    def __init__(self, localization_data, output_dir):
        self.OUTPUT_DIR = output_dir
        self.localizations_data = localization_data

    def run(self):
        os.makedirs(self.OUTPUT_DIR + '/localizations', exist_ok=True)
        for language, language_data in self.localizations_data.items():
            json_utils.write(
                self.OUTPUT_DIR + '/localizations/' + language + '.json',
                json_utils.sort_dict(language_data),
            )
