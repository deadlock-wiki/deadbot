import json
import os
import subprocess
from loguru import logger


class GameMapParser:
    def __init__(self, entity_helper_cmd, game_map_path):
        if not entity_helper_cmd:
            raise Exception('Config for DeadlockEntityHelper path is required for game map parsing')
        if not os.path.exists(entity_helper_cmd):
            raise Exception(f'Could not find DeadlockEntityHelper at path "{entity_helper_cmd}"')
        if not os.path.exists(game_map_path):
            raise Exception(f'Could not find game map at path "{game_map_path}"')

        self.entity_helper_cmd = entity_helper_cmd
        self.game_map_path = game_map_path

    def run(self):
        crates_data, statues_data = self._get_breakables_data()

        return {'crates': crates_data, 'statues': statues_data}

    def _get_breakables_data(self):
        breakables_properties = [
            'initial_spawn_time_override',
            'double',  # Used to identify breakables that are spawned late
            'scales',
            'vector3',  # Scale of the breakable
            'origin',
            'vector3',  # Position on the map
        ]

        return (
            self._extract_entities('citadel_breakable_prop_wooden_crate', *breakables_properties),
            self._extract_entities('citadel_breakable_item_container', *breakables_properties),
        )

    def _extract_entities(self, entity_subclass, *property_list) -> list:
        """
        Runs `DeadlockEntityHelper extract` with the specified arguments
        :param property_list: the remaining args are treated as property name-type pairs, e.g.:
            `_extract_entities('citadel_breakable_prop_wooden_crate', 'origin', 'vector3', 'subclass_name', 'string')`
        :return: a list of entity properties
        """
        args = [self.entity_helper_cmd, 'extract', '--verbose', self.game_map_path, entity_subclass, *property_list]
        helper_output = subprocess.run(args, capture_output=True, check=True, text=True)
        logger.trace(helper_output.stderr)

        return json.loads(helper_output.stdout)
