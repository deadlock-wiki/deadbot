import json
import os

# Insert a space before each capital letter except the first one
# "RoundsPerSecond" -> "Rounds Per Second"
def insert_space_before_capital(string):
    return ''.join([' ' + i if i.isupper() else i for i in string]).strip()

# TODO: Better name
# RoundsPerSecond -> rounds_per_second
def format_key(key):
    return insert_space_before_capital(key).replace(' ','_').lower()

def getInfoboxLine(key, value, max_key_length):
    return f"| {key.ljust(max_key_length)} = {str(value)}\n"

#TODO
def infobox_item():
    parameter_order = ["item_imagefilepath", "item_name", "item_type", 
                       "has_components", 
                       "has_passive1", "has_passive2", "has_passive3", "has_passive4", "has_active1", "has_active2", "has_active3", "has_active4"
                       "has_iscomponentof", 
                       "item_stat1", "item_stat2",
                       "souls", "iscomponentof1_name"]

# Converts hero json data to infobox hero template call
def infobox_hero(hero_data):
    # Order the parameters are provided to the Infobox template
    parameter_order = ["name", 
                       "dps", "bullet_damage", "clip_size", "rounds_per_second", "reload_time", "light_melee_damage", "heavy_melee_damage", 
                       "max_health", "health_regen", "bullet_resist", "spirit_resist", 
                       "max_move_speed", "sprint_speed", "stamina", 
                       "increase1_value", "increase1_stat", "increase2_value", "increase2_stat", "increase3_value", "increase3_stat", "increase4_value", "increase4_stat"]


    # Ensure all the hero data is in the parameter_order, used for catching changes to template calls or new hero data not yet handled
    for key, value in hero_data.items():
        excepted_keys = ["key"] #keys that don't need to be in the parameter_order
        if key not in parameter_order and key not in excepted_keys:
            print(f"{hero_data["Name"]}'s hero data {key} is not in the list of parameters")
            #return None

    # Sort hero_data's dict keys by the parameters in the parameter_order list
    # Tried for too long to get something that worked in less than O(a*b), maybe im missing something obvious
    infobox_data = {}
    for parameter in parameter_order:
        for key, value in hero_data.items():
            if parameter.endswith(format_key(key)): #i.e. melee_damage affects light_melee_damage and heavy_melee_damage
                infobox_data[key] = value
    
    
    

    # Calculate the maximum length of keys to align the values
    max_key_length = max(len(format_key(key)) for key in infobox_data.keys())

    # Create the Infobox template
    infobox_template = "{{Infobox hero\n"

    # Pre-determine if scalars are present
    SpiritScaling_present = "SpiritScaling" in hero_data
    LevelScaling_present = "LevelScaling" in hero_data

    for key, value in infobox_data.items():
        # Append the spirit scaling value to the base value inside {{ss|}} template call
        if SpiritScaling_present and any(key.endswith(scalingStat) for scalingStat in hero_data["SpiritScaling"]) and key != "RoundsPerSecond": #if it has nonzero spirit scaling
            # Search for the scaled stat that ends with the current key
            for scalingStat in hero_data["SpiritScaling"]:
                if key.endswith(scalingStat):
                    if hero_data["SpiritScaling"][scalingStat] == 0.0:
                        break
                    value = str(value) + " {{ss|" + str(hero_data["SpiritScaling"][scalingStat]) + "}}"
                    break

        # Append the level scaling value to the base value inside {{ls|}} template call
        elif LevelScaling_present and any(key.endswith(scalingStat) for scalingStat in hero_data["LevelScaling"]): #if it has nonzero level scaling
            #ls template still needs to be created; infobox uses a different formatting than this currently
            # Search for the scaled stat that ends with the current key
            for scalingStat in hero_data["LevelScaling"]:
                if key.endswith(scalingStat):
                    if hero_data["LevelScaling"][scalingStat] == 0.0:
                        break
                    value = str(value) + " {{ls|" + str(hero_data["LevelScaling"][scalingStat]) + "}}"
                    break

        elif format_key(key) not in parameter_order:
            continue # Skip keys not in the parameter_order


        # Format the key
        formatted_key = format_key(key)

        # Align the key with spaces to the max length
        infobox_template += getInfoboxLine(formatted_key, value, max_key_length)


        # Grey Talon has rounds per second scaling and fire rate scaling listed; though only base rounds per second is in data.
        # The rounds per second scalar is equivalent to the fire rate scalar, but only the fire rate one's intuitive application is correct because the rounds per second one implies that its 
        # (RPS + RPS from spirit) * Fire rate 
        # when its really 
        # RPS * Fire rate + RPS from spirit which is equal to RPS * (Fire rate + Fire rate from spirit)
        # Therefore, the scaling should only be displayed for fire rate. There are no other spirit scalars for stats that have final multipliers where this would be replicated.
        if key == "RoundsPerSecond":
            formatted_key = format_key("FireRate")
            value = "0% {{ss|" + str(hero_data["SpiritScaling"]["FireRate"]) + "}}"
            infobox_template += getInfoboxLine(formatted_key, value, max_key_length)


    infobox_template += "}}\n"

    return infobox_template

if __name__ == '__main__':
    # Example
    hero_data = {
        "BulletResist": 10.0,
        "AbilityResourceMax": 0,
        "AbilityResourceRegenPerSecond": 0,
        "ClipSize": 17,
        "HealthRegen": 2.0,
        "BulletDamage": 22.0,
        "RoundsPerSecond": 2.5,
        "CritDamageReceivedScale": 1.0,
        "CrouchSpeed": 4.75,
        "Dps": 55.0,
        "HeavyMeleeDamage": 116,
        "LevelScaling": {
            "BulletDamage": 1.46,
            "MeleeDamage": 3.4,
            "Health": 27.0,
            "TechDamagePerc": 0.0,
            "BulletResist": 0.0
        },
        "LightMeleeDamage": 63,
        "MaxHealth": 550,
        "MaxMoveSpeed": 6,
        "MoveAcceleration": 4,
        "Name": "Grey Talon",
        "ProcBuildUpRateScale": 1,
        "ReloadSpeed": 1,
        "ReloadTime": 2.35,
        "SprintSpeed": 0,
        "Stamina": 3,
        "StaminaRegenPerSecond": 0.2,
        "TechDuration": 1,
        "TechRange": 1,
        "SpiritScaling": {
            "MaxMoveSpeed": 0.04,
            "RoundsPerSecond": 0.00625,
            "FireRate": 0.25
        },
        "WeaponPower": 0,
        "WeaponPowerScale": 1
    }

    infobox = infobox_hero(hero_data)
    print(infobox)

            
