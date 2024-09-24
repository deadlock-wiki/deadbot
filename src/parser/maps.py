TARGET_TYPE_MAP = {
    'CITADEL_UNIT_TARGET_ALL_ENEMY': 'AllEnemy',
    'CITADEL_UNIT_TARGET_ALL_FRIENDLY': 'AllFriendly',
    'CITADEL_UNIT_TARGET_CREEP_ENEMY': 'CreepEnemy',
    'CITADEL_UNIT_TARGET_HERO_ENEMY': 'HeroEnemy',
    'CITADEL_UNIT_TARGET_HERO_FRIENDLY': 'HeroFriendly',
    'CITADEL_UNIT_TARGET_HERO': 'Hero',
    'CITADEL_UNIT_TARGET_MINION_ENEMY': 'MinionEnemy',
    'CITADEL_UNIT_TARGET_MINION_FRIENDLY': 'MinionFriendly',
    'CITADEL_UNIT_TARGET_NEUTRAL': 'Neutral',
    'CITADEL_UNIT_TARGET_PROP_ENEMY': 'PropEnemy',
    'CITADEL_UNIT_TARGET_TROOPER_ENEMY': 'TrooperEnemy',
    'CITADEL_UNIT_TARGET_TROPHY_ENEMY': 'TrophyEnemy',
}


def get_target_type(value):
    if value not in TARGET_TYPE_MAP:
        raise Exception(f'{value} is not a valid target type')
    return TARGET_TYPE_MAP.get(value)


SLOT_TYPE_MAP = {
    'EItemSlotType_WeaponMod': 'Weapon',
    'EItemSlotType_Armor': 'Armor',
    'EItemSlotType_Tech': 'Tech',
}


def get_slot_type(value):
    if value is None:
        return None

    if value not in SLOT_TYPE_MAP:
        raise Exception(f'{value} is not a valid slot type')
    return SLOT_TYPE_MAP.get(value)


def get_tier(value):
    if value is None:
        return None
    return value.replace('EModTier_', '')


def get_shop_filter(value):
    return value.replace('EShopFilter', '')


ABILITY_ACTIVATION_MAP = {
    'CITADEL_ABILITY_ACTIVATION_INSTANT_CAST': 'InstantCast',
    'CITADEL_ABILITY_ACTIVATION_PASSIVE': 'Passive',
    'CITADEL_ABILITY_ACTIVATION_PRESS': 'ActivationPress',
}


def get_ability_activation(value):
    if value is None:
        return None
    if value not in ABILITY_ACTIVATION_MAP:
        raise Exception(f'{value} is not a valid ability activation type')
    return ABILITY_ACTIVATION_MAP.get(value)


# i.e. ECitadelStat_Vitality -> Vitality
def get_attr_group(value):
    return value.split('ECitadelStat_')[1]


# i.e. m_eWeaponStatsDisplay -> Weapon
def get_shop_attr_group(value):
    if not value.startswith('m_e') or not value.endswith('StatsDisplay'):
        raise Exception(f'{value} is not a valid shop attribute group')
    return value.split('m_e')[1].split('StatsDisplay')[0]


def get_hero_attr(value):
    # Remove the 'E' prefix if its prefixed
    if value.startswith('E'):
        value = value[len('E') :]

    remaps = {'WeaponPower': 'BaseWeaponDamageIncrease', 'ClipSizeBonus': 'ClipSize'}

    if value in remaps:
        return remaps[value]

    remaps = {'WeaponPower': 'BaseWeaponDamageIncrease', 'ClipSizeBonus': 'ClipSize'}

    if value in remaps:
        return remaps[value]

    return value


# Maps label/postfixes for attributes that need to be manually mapped
# because they are not in the localization files as the same text
ATTRIBUTE_MANUAL_MAP = {
    'ClipSize': {'label': 'StatDesc_ClipSizeBonus'},
    'TechCooldownBetweenChargeUses': {
        'label': 'StatDesc_TechCooldownBetweenCharges',
        'postfix': 'StatDesc_TechCooldownBetweenCharges_postfix',
    },
    'MaxMoveSpeed': {'label': 'MoveSpeedMax_label', 'postfix': 'MoveSpeedMax_postfix'},
    'BaseWeaponDamageIncrease': {'label': 'WeaponPower_label', 'postfix': 'WeaponPower_postfix'},
}


def get_attr_manual_map():
    return ATTRIBUTE_MANUAL_MAP


LEVEL_MOD_MAP = {
    'MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL': 'BulletDamage',
    'MODIFIER_VALUE_BASE_MELEE_DAMAGE_FROM_LEVEL': 'MeleeDamage',
    'MODIFIER_VALUE_BASE_HEALTH_FROM_LEVEL': 'Health',
    'MODIFIER_VALUE_TECH_DAMAGE_PERCENT': 'TechDamagePerc',
    'MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST': 'BulletResist',
    'MODIFIER_VALUE_BONUS_ATTACK_RANGE': 'BonusAttackRange',
}


def get_level_mod(value):
    if value not in LEVEL_MOD_MAP:
        raise Exception(f'{value} is not a valid level mod')
    return LEVEL_MOD_MAP.get(value)


# Get last part of the snake-case ability name
# Eg. ESlot_Ability_Innate_1 -> Innate1
def get_bound_abilities(value):
    parts = list(value.split('_'))
    if len(parts) == 4:
        return parts[2] + parts[3]
    return parts[2]


KEYBIND_MAP = {
    'iv_attack': 'M1',
    'iv_attack2': 'M2',
    'key_alt_cast': 'M3',
    'key_reload': 'R',
    'key_innate_1': 'Shift',
    'in_mantle': 'Space',
    'key_duck': 'Ctrl',
    'in_ability1': '1',
    'in_ability2': '2',
    'in_ability3': '3',
    'in_ability4': '4',
}

LOCALIZATION_OVERRIDE_MAP = {
    'HealthSwapBuffDuration': 'SelfBuffDuration',
    'PounceDebuffRadius': 'ExplodeRadius',
    'DamageMissingPercentHealth': 'DamagePercentHealth',
    'AirDropExplodeRadius': 'OnLandDamageRadius',
    'AirDropBulletArmorReduction': 'BulletArmorReduction',
    'AirDropDebuff02Duration': 'BulletArmorReductionDuration',
    'AirDropSilenceDuration': 'SilenceDuration',
    'NormalDPS_scale': 'NormalDPS',
    'HotDPS_scale': 'HotDPS',
    'Damage_scale': 'Damage',
    'MaxChargeDuration': 'SpeedBoostDuration',
}


def override_localization(attr):
    """
    Get override key based on the variable names that are embedded in localization strings.
    If none exists in the map, return the original.

    This is designed to override the original keys for cases where the data key does not match
    the key in the localized string
    """
    if attr in LOCALIZATION_OVERRIDE_MAP:
        return LOCALIZATION_OVERRIDE_MAP[attr]
    else:
        return attr


SCALE_TYPE_MAP = {
    'ETechPower': 'spirit',
    'ELightMeleeDamage': 'melee',
    'ETechRange': 'range',
    'ETechCooldown': 'cooldown',
    'EBulletDamage': 'damage',
    'ETechDuration': 'duration',
}


def get_scale_type(scale):
    if scale is None:
        return scale

    if scale not in SCALE_TYPE_MAP:
        raise Exception(f'No scale map found for {scale}')

    return SCALE_TYPE_MAP[scale]
