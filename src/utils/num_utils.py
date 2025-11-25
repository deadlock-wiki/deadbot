import math
from constants import ENGINE_UNITS_PER_METER


def convert_engine_units_to_meters(engine_units: int | float, sigfigs: int = 4) -> float:
    """
    Convert engine units to meters with proper precision handling.
    Eliminates floating-point artifacts by rounding to a reasonable precision.

    Args:
        engine_units: Raw value in engine units
        sigfigs: Number of significant figures to round to (default: 4)

    Returns:
        Value in meters, rounded and cleaned of floating-point artifacts
    """
    if engine_units is None or engine_units == 0:
        return engine_units

    meters = engine_units / ENGINE_UNITS_PER_METER
    # Round to specified significant figures to avoid floating-point precision artifacts
    return round_sig_figs(meters, sigfigs)


def assert_number(value: int | float | str):
    """
    Ensure any input numbers, or stringified numbers are converted
    to their appropriate type

    Otherwise, return original value
    """
    if isinstance(value, float):
        return fix_float_garbage(value)

    if isinstance(value, int):
        return value

    if value is None:
        return value

    # stringified float will always have a decimal point
    if '.' in value:
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def fix_float_garbage(x: float, max_decimals=3, eps=1e-5):
    """
    Round values if they appear to have float artifacts
    Eg. 12.599999 should be rounded as 12.6, as the excess precision is not helpful

    Args:
        x (float): Float value to be rounded
        max_decimals (int, optional): Maximum decimal places to round to. Defaults to 3.
        eps (_type_, optional): Minimum difference to the rounded value that deems the float as garbage. Defaults to 1e-5.

    Returns:
        float: If garbage, return rounded value, otherwise return the original
    """
    for d in range(1, max_decimals + 1):
        candidate = round(x, d)
        if abs(x - candidate) < eps:
            return candidate
    return x


def remove_uom(value):
    """
    Check if a value is just a number with a unit of measurement at the end.
    If it is, return the number, else the original string

    Possible units of measurement include metres (m) and seconds(s)
    """
    if not isinstance(value, str):
        return value

    string = value
    if string.endswith('m') or string.endswith('s'):
        stripped_string = assert_number(string[:-1])
        # if string is returned, that means it could have just been word ending with s or m
        if isinstance(stripped_string, str):
            return string
        return stripped_string
    return assert_number(string)


def is_zero(value):
    """Checks if a value is zero reliably, as to avoid the edge case where False==0 -> True"""
    if isinstance(value, bool):
        return False

    if isinstance(value, (int, float)) and value == 0:
        return True

    return False


def round_sig_figs(value: float | int, sigfigs: int):
    if isinstance(value, float) and value == 0.0:
        return 0.0

    if value == 0:
        return 0

    return round(value, sigfigs - int(math.floor(math.log10(abs(value)))) - 1)
