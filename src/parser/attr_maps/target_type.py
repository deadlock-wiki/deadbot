TARGET_TYPE_MAP = {
    'CITADEL_UNIT_TARGET_ABILLITY_TRIGGER': 'AbilityTrigger',
    'CITADEL_UNIT_TARGET_ALL_ENEMY': 'AllEnemy',
    'CITADEL_UNIT_TARGET_ALL_FRIENDLY': 'AllFriendly',
    'CITADEL_UNIT_TARGET_ALL': 'All',
    'CITADEL_UNIT_TARGET_BOSS_ENEMY': 'BossEnemy',
    'CITADEL_UNIT_TARGET_BUILDING_ENEMY': 'BuildingEnemy',
    'CITADEL_UNIT_TARGET_CREEP_ENEMY': 'CreepEnemy',
    'CITADEL_UNIT_TARGET_CREEP_FRIENDLY': 'CreepFriendly',
    'CITADEL_UNIT_TARGET_GOLD_ORBS': 'GoldOrbs',
    'CITADEL_UNIT_TARGET_HERO_ENEMY': 'HeroEnemy',
    'CITADEL_UNIT_TARGET_HERO_FRIENDLY': 'HeroFriendly',
    'CITADEL_UNIT_TARGET_HERO': 'Hero',
    'CITADEL_UNIT_TARGET_MINION_ENEMY': 'MinionEnemy',
    'CITADEL_UNIT_TARGET_MINION_FRIENDLY': 'MinionFriendly',
    'CITADEL_UNIT_TARGET_NEUTRAL': 'Neutral',
    'CITADEL_UNIT_TARGET_PROP_ENEMY': 'PropEnemy',
    'CITADEL_UNIT_TARGET_PROP_FRIENDLY': 'PropFriendly',
    'CITADEL_UNIT_TARGET_TROOPER_ENEMY': 'TrooperEnemy',
    'CITADEL_UNIT_TARGET_TROOPER_FRIENDLY': 'TrooperFriendly',
    'CITADEL_UNIT_TARGET_TROPHY_ENEMY': 'TrophyEnemy',
    'CITADEL_UNIT_TARGET_TROPHY_FRIENDLY': 'TrophyFriendly',
    'CITADEL_UNIT_TARGET_NONE': None,
    None: None,
}


def get_target_type(value):
    if value not in TARGET_TYPE_MAP:
        raise Exception(f'{value} is not a valid target type')
    return TARGET_TYPE_MAP.get(value)
