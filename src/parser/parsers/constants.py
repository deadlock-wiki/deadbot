OUTPUT_DIR = '../../output-data/'


# Lower and upper bound from 3 samples checked in game manually due to rounding
# I.e., 610m/s velocity in game could actually be anywhere from 609-611 without knowing the rounding
# These represent the engine units per in game meter
# This represents the average of the lower and upper bound
ENGINE_UNITS_PER_METER = (39.33 + 39.4) / 2
