import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import json_utils


LOCALIZATION_PATH = 'src/parser/decompiler/decompiled-data/localizations'
LOCALIZATION_GROUPS = ['attributes', 'gc', 'heroes', 'main', 'mods']


def get_localized_text(unlocalized_text, language, localization_group, dir_pre_shift=''):
    if localization_group not in LOCALIZATION_GROUPS:
        raise ValueError(f'Invalid localization group: {localization_group}')

    path = os.path.join(
        dir_pre_shift+LOCALIZATION_PATH, localization_group, f'citadel_{localization_group}_{language}.json'
    )  # i.e src/parser/decompiled-data/localizations/citadel_attributes_english.json

    # Redirect to another localization group
    # (text_thats_missing_localization, ' '.join[(redirected_text_to_localize, localization_group)])
    # i.e. CrouchSpeed becomes guide_movement_crouch_header.localize + StatDesc_RunSpeed.localize = Crouch Move Speed (english)
    redirects = [('Name', [('Citadel_HeroBuilds_CategoryNameLabel', 'main')]),
                 ('CrouchSpeed', [('guide_movement_crouch_header', 'main'), ('StatDesc_RunSpeed', 'attributes')]),
                 ]
    for redirect in redirects:
        text_thats_missing_localization = redirect[0]
        if unlocalized_text.lower() == text_thats_missing_localization.lower():
            redirect_components = redirect[1]
            localized_texts = []
            for redirect_component in redirect_components:
                redirected_text_to_localize = redirect_component[0]
                localization_group = redirect_component[1]
                localized_texts.append(get_localized_text(redirected_text_to_localize, language, localization_group, dir_pre_shift))
            return ' '.join(localized_texts) 
    
    with open(path, 'r', encoding='utf-8') as f:
        localization_data = json.load(f)

        # Remap keys that are missing from localization data
        remap = {
            "ClipSize": "ClipSizeBonus",
            "MaxMoveSpeed": "MoveSpeedMax",
            "MoveAcceleration": "RunAcceleration",
        }

        # If the value is in the remap, return the remapped value
        unlocalized_text = remap.get(unlocalized_text, unlocalized_text)

        #Localize the text if possible, else return the original text
        # Check if the key is "StatDesc_"+k, k+"_label", or k
        localized = localization_data.get('StatDesc_'+unlocalized_text, None) 
        if localized is None:
            localized = localization_data.get(unlocalized_text+'_label', None)
        if localized is None:
            localized = localization_data.get(unlocalized_text, None)

        # Get the localized postfix like m/s or % as well

        return localized
        


# Convert language to the language code/abbreviation that will eventually be used in the wiki link
# english -> en
# spanish -> es, etc.
def get_language_abbrev(language):
    return language  # TODO
