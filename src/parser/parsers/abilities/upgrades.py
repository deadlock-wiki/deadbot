from parser import maps
from . import utils
from utils import json_utils, num_utils
from typing import TypedDict


class ScaleEntry(TypedDict):
    Value: int | float
    Type: str | None


class UpgradeWithScale(TypedDict):
    Value: int | float
    Scale: ScaleEntry | list[ScaleEntry]


ParsedUpgradeValue = int | float | UpgradeWithScale

ParsedUpgradeSet = dict[str, ParsedUpgradeValue]


# Raw intermediate used during parsing
class RawUpgrade(TypedDict):
    prop: str | None
    value: int | float
    upgrade_type: str | None
    scale_type: str | None


def parse_upgrades(ability):
    upgrade_sets = ability['m_vecAbilityUpgrades']
    parsed_upgrade_sets = []

    for upgrade_set in upgrade_sets:
        upgrades = upgrade_set.get('m_vecPropertyUpgrades')
        if upgrades is None:
            continue

        # 1. Extract raw data from each upgrade entry
        raw_upgrades: list[RawUpgrade] = []
        for upgrade in upgrades:
            prop = upgrade.get('m_strPropertyName')
            raw_value = upgrade.get('m_strBonus')
            upgrade_type = upgrade.get('m_eUpgradeType')
            scale_type = upgrade.get('m_eScaleStatFilter')

            value = num_utils.assert_number(raw_value)

            stat = json_utils.deep_get(ability, 'm_mapAbilityProperties', prop)
            if stat:
                value = utils.convert_stat(stat, raw_value, value)

            raw_upgrades.append(
                {
                    'prop': prop,
                    'value': value,
                    'upgrade_type': upgrade_type,
                    'scale_type': scale_type,
                }
            )

        # 2. Group by prop so we can reason about base + scales together
        upgrades_by_prop: dict[str, list[RawUpgrade]] = {}
        for raw in raw_upgrades:
            upgrades_by_prop.setdefault(raw['prop'], []).append(raw)

        # 3. Build the parsed upgrade set from grouped data
        parsed_upgrade_set: ParsedUpgradeSet = {}
        for prop, entries in upgrades_by_prop.items():
            base_value: int | float = 0
            scales: list[ScaleEntry] = []

            for entry in entries:
                if entry['upgrade_type'] in ['EAddToBase', None]:
                    base_value = entry['value']
                elif entry['upgrade_type'] in ['EAddToScale', 'EMultiplyScale']:
                    scale_type = entry['scale_type']
                    if scale_type is None:
                        base_stat = json_utils.deep_get(ability, 'm_mapAbilityProperties', prop)
                        if base_stat and 'm_subclassScaleFunction' in base_stat:
                            scale_func = base_stat['m_subclassScaleFunction']
                            scale_type = scale_func.get('m_eSpecificStatScaleType')
                            if scale_type is None and 'tech' in scale_func.get('_class', ''):
                                scale_type = 'ETechPower'
                    scales.append(
                        {
                            'Value': entry['value'],
                            'Type': maps.get_scale_type(scale_type),
                        }
                    )

            if scales:
                # if there are multiple scales for a prop, output as an array
                if len(scales) > 1:
                    parsed_upgrade_set[prop] = {'Value': base_value, 'Scale': scales}
                else:
                    parsed_upgrade_set[prop] = {'Value': base_value, 'Scale': scales[0]}
            else:
                parsed_upgrade_set[prop] = base_value

        parsed_upgrade_sets.append(parsed_upgrade_set)

    return parsed_upgrade_sets
