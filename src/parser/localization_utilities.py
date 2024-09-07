import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils


LOCALIZATION_PATH = 'src/parser/decompiler/decompiled-data/localizations'
LOCALIZATION_GROUPS = ['attributes', 'gc', 'heroes', 'main', 'mods']


def get_localized_text(unlocalized_text, language, localization_group):
    if localization_group not in LOCALIZATION_GROUPS:
        raise ValueError(f'Invalid localization group: {localization_group}')

    path = os.path.join(
        LOCALIZATION_PATH, localization_group, f'citadel_{localization_group}_{language}.json'
    )  # i.e src/parser/decompiled-data/localizations/citadel_attributes_english.json
    
    # Retrieve abilities data
    abilities_data = json_utils.read('src/parser/decompiler/decompiled-data/scripts/abilities.json')

    with open(path, 'r', encoding='utf-8') as f:
        localization_data = json.load(f)


        #TODO use attribute-localization-data.json

        #Localize the text if possible, else return the original text
        return localization_data.get('StatDesc_'+unlocalized_text, None) 
        


# Convert language to the language code/abbreviation that will eventually be used in the wiki link
# english -> en
# spanish -> es, etc.
def get_language_abbrev(language):
    return language  # TODO
