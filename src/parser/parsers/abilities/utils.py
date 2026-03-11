from utils import num_utils


def convert_stat(stat: dict, key: str, value: str | int | float):
    """Convert a value to the correct unit of measure and format based on the raw stat's information

    Args:
        stat (dict): Raw ability stat which includes information on its units and class
        key (str): Key of ability stat
        value (str | int | float): Value of ability stat

    Returns:
        int | float: Converted value
    """
    # if the value ends with "m", it is already converted to the correct units
    if isinstance(value, str) and value.endswith('m'):
        return num_utils.assert_number(value[:-1])

    # specific to ChannelMoveSpeed, a "-1" indicates stationary, so no need to convert units
    if key == 'ChannelMoveSpeed' and value == '-1':
        return -1

    units = stat.get('m_eDisplayUnits')
    strClass = stat.get('m_strCSSClass')

    # some ranges are written as "1500 2000" to denote a specific range
    if isinstance(value, str) and strClass == 'range':
        ranges = value.split(' ')
        if len(ranges) == 2:
            lower = num_utils.assert_number(ranges[0])
            upper = num_utils.assert_number(ranges[1])
            if units in ['EDisplayUnit_Meters', 'EDisplayUnit_MetersPerSecond']:
                return f'{num_utils.convert_engine_units_to_meters(lower)} {num_utils.convert_engine_units_to_meters(upper)}'
            else:
                return f'{lower} {upper}'

    value = num_utils.assert_number(value)

    if units in ['EDisplayUnit_Meters', 'EDisplayUnit_MetersPerSecond']:
        return num_utils.convert_engine_units_to_meters(value)

    return value
