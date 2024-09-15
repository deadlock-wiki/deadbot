import re

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
        value = value[1:]

    return value


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


def get_uom(attr):
    """get unit of measurement based on attribute"""
    if 'Cooldown' in attr:
        return 's'

    if 'Duration' in attr:
        return 's'

    return ''


def get_ability_display_name(attr):
    # strip out redundant "Ability"
    if attr.startswith('Ability'):
        attr = attr[7:]
    return pascal_to_words(attr)


def pascal_to_words(text):
    """Convert pascal text to be spaced.
    Eg. NeverGonnaGiveYouUp -> Never Gonna Give You Up
    """

    # ensure DPS is preserved as caps
    if 'DPS' in text:
        text.replace('DPS', 'Dps')

    pascal_case = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)

    # return DPS back
    return pascal_case.replace('Dps', 'DPS')
