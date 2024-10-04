import sys
import os
from .localization_objects import Localization

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import maps as maps
import utils.json_utils as json_utils


class LocalizationParser:
    def __init__(self, localization_data, output_dir):
        self.OUTPUT_DIR = output_dir
        self.localizations_data = localization_data

    def run(self):
        all_localizations = {}
        for language, language_data in self.localizations_data.items():
            all_localizations[language] = json_utils.sort_dict(language_data)
        Localization.hash_to_objs(json_utils.sort_dict(all_localizations))
        # Localization.save_all_langs()
        Localization.save_objects()
