TARGETING_LOCATION_MAP = {
    'CITADEL_ABILITY_TARGETING_LOCATION_GROUND': 'Ground',
    'CITADEL_ABILITY_TARGETING_LOCATION_MINIMAP_UNIT': 'MinimapUnit',
    'CITADEL_ABILITY_TARGETING_LOCATION_SELF': 'Self',
    'CITADEL_ABILITY_TARGETING_LOCATION_UNIT': 'Unit',
    'CITADEL_ABILITY_TARGETING_LOCATION_NONE': None,
    None: None,
}


def get_targeting_location(value):
    if value not in TARGETING_LOCATION_MAP:
        raise Exception(f'{value} is not a valid targeting location')
    return TARGETING_LOCATION_MAP.get(value)
