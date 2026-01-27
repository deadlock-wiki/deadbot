TARGET_TYPE_MAP = {
    'CITADEL_UNIT_TARGET_ALL_ENEMY': 'AllEnemy',
    'CITADEL_UNIT_TARGET_ALL_FRIENDLY': 'AllFriendly',
    'CITADEL_UNIT_TARGET_BOSS_ENEMY': 'BossEnemy',
    'CITADEL_UNIT_TARGET_CREEP_ENEMY': 'CreepEnemy',
    'CITADEL_UNIT_TARGET_HERO_ENEMY': 'HeroEnemy',
    'CITADEL_UNIT_TARGET_HERO_FRIENDLY': 'HeroFriendly',
    'CITADEL_UNIT_TARGET_HERO': 'Hero',
    'CITADEL_UNIT_TARGET_MINION_ENEMY': 'MinionEnemy',
    'CITADEL_UNIT_TARGET_MINION_FRIENDLY': 'MinionFriendly',
    'CITADEL_UNIT_TARGET_NEUTRAL': 'Neutral',
    'CITADEL_UNIT_TARGET_PROP_ENEMY': 'PropEnemy',
    'CITADEL_UNIT_TARGET_TROOPER_ENEMY': 'TrooperEnemy',
    'CITADEL_UNIT_TARGET_TROOPER_FRIENDLY': 'TrooperFriendly',
    'CITADEL_UNIT_TARGET_TROPHY_ENEMY': 'TrophyEnemy',
}


def get_target_type(value):
    if value not in TARGET_TYPE_MAP:
        raise Exception(f'{value} is not a valid target type')
    return TARGET_TYPE_MAP.get(value)


SOUL_UNLOCK_MAP = {
    'm_unRequiredGold': 'RequiredSouls',
    'EAbilityUnlocks': 'AbilityUnlocks',
    'EAbilityPoints': 'AbilityPoints',
    'm_bUseStandardUpgrade': 'PowerIncrease',
}


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
    'CITADEL_ABILITY_ACTIVATION_PRESS_TOGGLE': 'Toggle',
    'CITADEL_ABILITY_ACTIVATION_PRESS': 'Press',
    'CITADEL_ABILITY_ACTIVATION_INSTANT_CAST_TOGGLE': 'InstantCastToggle',
    'CITADEL_ABILITY_ACTIVATION_ON_BUTTON_RELEASE': 'OnRelease',
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

    remaps = {
        'WeaponPower': 'BaseWeaponDamageIncrease',
        'ClipSizeBonus': 'ClipSize',
        'BulletArmorDamageReduction': 'BulletResist',
        'TechArmorDamageReduction': 'TechResist',
    }

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
    'OOCHealthRegen': {
        'label': 'OutOfCombatHealthRegen_label',
        'postfix': 'OutOfCombatHealthRegen_prefix',
    },
}


def get_attr_manual_map():
    return ATTRIBUTE_MANUAL_MAP


LEVEL_MOD_MAP = {
    'MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL': 'BulletDamage',
    'MODIFIER_VALUE_BASE_BULLET_DAMAGE_FROM_LEVEL_ALT_FIRE': 'BulletDamageAltFire',
    'MODIFIER_VALUE_BASE_MELEE_DAMAGE_FROM_LEVEL': 'MeleeDamage',
    'MODIFIER_VALUE_BASE_HEALTH_FROM_LEVEL': 'MaxHealth',
    'MODIFIER_VALUE_TECH_DAMAGE_PERCENT': 'TechDamagePerc',
    'MODIFIER_VALUE_TECH_ARMOR_DAMAGE_RESIST': 'TechResist',
    'MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST': 'BulletResist',
    'MODIFIER_VALUE_BONUS_ATTACK_RANGE': 'BonusAttackRange',
    'MODIFIER_VALUE_BOON_COUNT': 'PowerIncreases',
    'MODIFIER_VALUE_TECH_POWER': 'TechPower',
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


LOCALIZATION_OVERRIDE_MAP = {
    'MaxChargeDuration': 'SpeedBoostDuration',
    'MinDPS': 'MinDps',
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
    'EBaseWeaponDamageIncrease': 'weapon_damage_increase',
    'EBulletDamage': 'damage',
    'EHealingOutput': 'healing',
    'EHeavyMeleeDamage': 'heavy_melee',
    'ELevelUpBoons': 'power_increase',
    'ELightMeleeDamage': 'melee',
    'EMaxChargesIncrease': 'max_charges',
    'EStatsCount': 'stats_count',
    'ETechCooldown': 'cooldown',
    'ETechDuration': 'duration',
    'ETechPower': 'spirit',
    'ETechRange': 'range',
    'EWeaponDamageScale': 'weapon_damage',
    'EWeaponPower': 'weapon_power',
}


def get_scale_type(scale):
    if scale is None:
        return scale

    if scale not in SCALE_TYPE_MAP:
        raise Exception(f'No scale map found for {scale}')

    return SCALE_TYPE_MAP[scale]


NPC_INTRINSIC_MODIFIER_MAP = {
    'MODIFIER_VALUE_BULLET_DAMAGE_REDUCTION_PERCENT': 'IntrinsicBulletResistance',
    'MODIFIER_VALUE_ABILITY_DAMAGE_REDUCTION_PERCENT': 'IntrinsicAbilityResistance',
    'MODIFIER_VALUE_HEALTH_REGEN_PER_SECOND': 'HealthRegenPerSecond',
}


def get_npc_intrinsic_modifier(value):
    return NPC_INTRINSIC_MODIFIER_MAP.get(value)


NPC_AURA_MODIFIER_MAP = {
    'MODIFIER_VALUE_TECH_ARMOR_DAMAGE_RESIST': 'FriendlyAuraSpiritArmor',
    'MODIFIER_VALUE_BULLET_ARMOR_DAMAGE_RESIST': 'FriendlyAuraBulletArmor',
}


def get_npc_aura_modifier(value):
    return NPC_AURA_MODIFIER_MAP.get(value)


NPC_REBIRTH_MODIFIER_MAP = {
    'MODIFIER_VALUE_HEALTH_MAX_PERCENT': 'BonusMaxHealth',
    'MODIFIER_VALUE_FIRE_RATE': 'BonusFireRate',
    'MODIFIER_VALUE_TECH_DAMAGE_PERCENT': 'BonusSpiritDamage',
}


def get_npc_rebirth_modifier(value):
    return NPC_REBIRTH_MODIFIER_MAP.get(value)
