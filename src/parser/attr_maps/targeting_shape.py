TARGETING_SHAPE_MAP = {
    'CITADEL_ABILITY_TARGETING_SHAPE_LINE': 'Line',
    'CITADEL_ABILITY_TARGETING_SHAPE_SPHERE': 'Sphere',
    'CITADEL_ABILITY_TARGETING_SHAPE_CIRCLE': 'Circle',
    'CITADEL_ABILITY_TARGETING_SHAPE_CONE': 'Cone',
    'CITADEL_ABILITY_TARGETING_SHAPE_NONE': None,
    None: None,
}


def get_targeting_shape(value):
    if value not in TARGETING_SHAPE_MAP:
        raise Exception(f'{value} is not a valid targeting shape')
    return TARGETING_SHAPE_MAP.get(value)
