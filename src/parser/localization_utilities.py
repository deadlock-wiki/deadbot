import os
import json

LOCALIZATION_PATH = "src/parser/decompiled-data/localizations"
LOCALIZATION_GROUPS = ["attributes","gc","heroes","main","mods"]

def get_localized_text(unlocalized_text, language, localization_group):
    if localization_group not in LOCALIZATION_GROUPS:
        raise ValueError(f"Invalid localization group: {localization_group}")
    
    path = os.path.join(LOCALIZATION_PATH, localization_group, f"citadel_{localization_group}_{language}.json") #i.e src/parser/decompiled-data/localizations/citadel_attributes_english.json

    with open(path, 'r', encoding='utf-8') as f:
        localization_data = json.load(f)

        
        # Adjust data, unfortunately its not 1 to 1 oddly enough
        data = {}
        for key,value in localization_data.items():
            # Remove Bonus if its a prefix from all keys
            if key.startswith("Bonus"):
                key = key[len("Bonus"):]

            # Remove Total_label if its a suffix from all keys
            if key.endswith("Total_label"):
                key = key[:-len("Total_label")]+"_label"

            data[key] = value
                
        if unlocalized_text+"_label" in data:
            localized_text = data.get(unlocalized_text+"_label")
        elif "StatDesc_"+unlocalized_text in data:
            localized_text = data.get("StatDesc_"+unlocalized_text)
        else:
            localized_text = language+unlocalized_text
            print(f"Could not find localized text for {unlocalized_text} in {path}")


        return localized_text

# Convert language to the language code/abbreviation that will eventually be used in the wiki link
# english -> en
# spanish -> es, etc.
def get_language_abbrev(language):
    return language #TODO
    
