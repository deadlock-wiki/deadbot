import os
import utils.json_utils as json_utils

OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../../output-data/')

class Localization:
    def __init__(self, lang='english'):
        self.localization_data = {}
        self.localization_data[lang] = json_utils.read(OUTPUT_DIR + '/localizations/' + lang + '.json')

    def _localize(self, key, lang='english'):
        return self.localization_data[lang].get(key, key)