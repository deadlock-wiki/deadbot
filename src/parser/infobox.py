import json
import os

# Insert a space before each capital letter except the first one
# "BulletsPerSec" -> "Bullets Per Sec"
def insert_space_before_capital(string):
    return ''.join([' ' + i if i.isupper() else i for i in string]).strip()

# Converts hero json data to infobox hero template call
def infobox_hero(hero_data):
    # Order the parameters are provided to the Infobox template
    parameter_order = ["name", "art", "card", "summary", "description", 
                       "dps", "bullet_damage", "ammo", "bullets_per_sec", "light_melee", "heavy_melee", 
                       "max_health", "health_regen", "bullet_resist", "spirit_resist", 
                       "move_speed", "sprint_speed", "stamina", 
                       "increase1_value", "increase1_stat", "increase2_value", "increase2_stat", "increase3_value", "increase3_stat", "increase4_value", "increase4_stat"]

    # Alter the key's format to match the parameter
    hero_data_reformatted = {}
    for key, value in hero_data.items():
        # Convert the key from BulletsPerSec to bullets_per_sec
        key = insert_space_before_capital(key).replace(' ','_').lower()
        hero_data_reformatted[key] = value

    # Ensure all the hero data is in the parameter_order, used for catching changes to template calls or new hero data not yet handled
    for key, value in hero_data_reformatted.items():
        excepted_keys = ["key"] #keys that don't need to be in the parameter_order
        if key not in parameter_order and key not in excepted_keys:
            print(f"{hero_data_reformatted["name"]}'s hero data missing a parameter for infobox hero: {key}")
            #return None
    
    
    # Create a dictionary to store the data in the order it should be displayed
    infobox_data = {}
    for parameter in parameter_order:
        if parameter in hero_data_reformatted:
            infobox_data[parameter] = hero_data_reformatted[parameter]
        #else:
            #print(f"Hero data key '{key}' not in infobox hero's parameter_order")

    # Calculate the maximum length of keys to align the values
    max_key_length = max(len(key) for key in infobox_data.keys())

    # Create the Infobox template
    infobox_template = "{{Infobox hero\n"
    for key, value in infobox_data.items():
        # Align the key with spaces to the max length
        infobox_template += f"| {key.ljust(max_key_length)} = {value}\n"
    infobox_template += "}}\n"

    return infobox_template

def infobox_item():
    parameter_order = ["item_imagefilepath", "item_name", "item_type", 
                       "has_components", 
                       "has_passive1", "has_passive2", "has_passive3", "has_passive4", "has_active1", "has_active2", "has_active3", "has_active4"
                       "has_iscomponentof", 
                       "item_stat1", "item_stat2",
                       "souls", "iscomponentof1_name"]

if __name__ == '__main__':
    # Example
    hero_data = {
        "AbilityResourceMax": 0,
        "AbilityResourceRegenPerSecond": 0,
        "Ammo": 14,
        "BaseHealthPerLevel": 41.0,
        "BaseHealthRegen": 2.0,
        "BulletArmorPerLevel": 0.0,
        "BulletDamage": 3.24,
        "BulletDamagePerLevel": 0.0,
        "BulletsPerSec": 5.555555555555555,
        "CritDamageReceivedScale": 1.0,
        "CrouchSpeed": 4.75,
        "Dps": 18.0,
        "HeavyMeleeDamage": 116,
        "LightMeleeDamage": 63,
        "MaxHealth": 550,
        "MaxMoveSpeed": 7,
        "MeleeDamagePerLevel": 3.4,
        "MoveAcceleration": 4,
        "Name": "Rutger",
        "ProcBuildUpRateScale": 1,
        "ReloadSpeed": 1,
        "ReloadTime": 2.4,
        "SprintSpeed": 0,
        "Stamina": 3,
        "StaminaRegenPerSecond": 0.2,
        "TechDamagePercPerLevel": 0.0,
        "TechDuration": 1,
        "TechRange": 1,
        "WeaponPower": 0,
        "WeaponPowerScale": 1
    }

    infobox = infobox_hero(hero_data)
    print(infobox)

            
