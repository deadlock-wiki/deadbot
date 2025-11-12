import math
from constants import ENGINE_UNITS_PER_METER


def convert_engine_units_to_meters(engine_units: float, decimal_places: int = 2) -> float:
    """
    Convert engine units to meters with proper precision handling.
    Eliminates floating-point artifacts by rounding to a reasonable precision.

    Args:
        engine_units: Raw value in engine units
        decimal_places: Number of decimal places to round to (default: 2)

    Returns:
        Value in meters, rounded and cleaned of floating-point artifacts
    """
    if engine_units is None or engine_units == 0:
        return engine_units

    meters = engine_units / ENGINE_UNITS_PER_METER
    # Round to specified decimal places to avoid floating-point precision artifacts
    return round(meters, decimal_places)


def assert_number(value):
    """
    Ensure any input numbers, or stringified numbers are converted
    to their appropriate type

    Otherwise, return original value
    """
    if isinstance(value, float) | isinstance(value, int):
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
    if value == 0:
        return 0
    return round(value, sigfigs - int(math.floor(math.log10(abs(value)))) - 1)
