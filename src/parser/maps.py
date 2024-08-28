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
