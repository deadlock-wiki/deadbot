import sys
import os

# bring utils module in scope
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from .constants import OUTPUT_DIR
import utils.json_utils as json_utils
import utils.string_utils as string_utils


class AttributeParser:
    def __init__(self, parsed_heroes, localizations):
        self.heroes_data = parsed_heroes
        self.localizations = localizations

    def run(self):
        all_attributes = {}
        all_attributes = self._parse_stats_ui(self.heroes_data)

        json_utils.write(
            OUTPUT_DIR + 'json/attribute-data.json', json_utils.sort_dict(all_attributes)
        )

    # Move StatsUI data to attributes data
    def _parse_stats_ui(self, heroes_data):
        all_attributes = {}

        for hero_key, hero_value in heroes_data.items():
            if 'StatsUI' not in hero_value:
                continue

            stats_ui = hero_value['StatsUI']
            for ui_category, stats in stats_ui.items():
                if ui_category not in all_attributes:
                    all_attributes[ui_category] = []

                for stat_name in stats:
                
                    if stat_name not in all_attributes[ui_category]:    
                        all_attributes[ui_category].append(stat_name)

        return all_attributes
