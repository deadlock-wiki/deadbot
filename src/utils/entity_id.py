"""Derive the stable entity id used by build codes from a VData class name.

The game does not serialize the numeric id used in the clipboard build format.
It is the 32-bit MurmurHash2 of the class name with the same seed used by the
community asset pipelines (0x31415926), so it can be computed locally.

Examples:
    upgrade_clip_size        -> 1548066885
    upgrade_ability_refresher -> 677738769
    upgrade_berserker        -> 1414319208
"""

ENTITY_ID_SEED = 0x31415926
_M = 0x5BD1E995
_R = 24


def entity_id(class_name: str) -> int:
    data = class_name.encode('utf-8')
    length = len(data)
    h = (ENTITY_ID_SEED ^ length) & 0xFFFFFFFF

    i = 0
    while length - i >= 4:
        k = int.from_bytes(data[i:i + 4], 'little')
        k = (k * _M) & 0xFFFFFFFF
        k ^= k >> _R
        k = (k * _M) & 0xFFFFFFFF
        h = (h * _M) & 0xFFFFFFFF
        h ^= k
        i += 4

    remaining = length - i
    if remaining == 3:
        h ^= data[i + 2] << 16
    if remaining >= 2:
        h ^= data[i + 1] << 8
    if remaining >= 1:
        h ^= data[i]
        h = (h * _M) & 0xFFFFFFFF

    h ^= h >> 13
    h = (h * _M) & 0xFFFFFFFF
    h ^= h >> 15
    return h & 0xFFFFFFFF
