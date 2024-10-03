import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.json_utils as json_utils


class LocalizationParser:
    def __init__(self, localization_data, output_dir):
        self.OUTPUT_DIR = output_dir
        self.localizations_data = localization_data

    def run(self):
        for language, language_data in self.localizations_data.items():
            json_utils.write(self.OUTPUT_DIR+'/localizations/' + language + '.json',
                json_utils.sort_dict(language_data),
            )
