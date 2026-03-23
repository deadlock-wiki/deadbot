import json
import os
import subprocess

from loguru import logger
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


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
        midtown_crates_data, midtown_statues_data = self._get_breakables_data()

        midtown_crate_plot = self._midtown_crate_plot(midtown_crates_data)
        midtown_statues_plot = self._midtown_golden_statues_plot(midtown_statues_data)

        midtown_metadata = {'golden_statues_count': len(midtown_statues_data), 'crate_count': len(midtown_crates_data)}

        return {
            'midtown': {
                'plots': {
                    'crate': midtown_crate_plot,
                    'golden_statues': midtown_statues_plot,
                },
                'metadata': midtown_metadata,
            }
        }

    def _midtown_golden_statues_plot(self, statues_data):
        glitched_statues = [[-704, -2320.0002, 704], [704, 2320.0002, 704]]

        x_coords = []
        y_coords = []
        colors = []
        for entry in statues_data:
            x_coords.append(entry['origin'][0])
            y_coords.append(entry['origin'][1])
            if entry['scales'][0] < 0.85:
                colors.append('blue')
            elif entry['initial_spawn_time_override'] > 0:
                colors.append('green')
            elif entry['origin'] in glitched_statues:
                colors.append('red')
            else:
                colors.append('orange')

        from matplotlib.lines import Line2D

        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Vent access required', markerfacecolor='blue', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='T2 Statue (spawns after 10 minutes)', markerfacecolor='green', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Glitched Statue', markerfacecolor='red', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Normal Statue', markerfacecolor='orange', markersize=10),
        ]

        return self._create_plot(x_coords, y_coords, colors, legend_elements, 'midtown_golden_statues')

    def _midtown_crate_plot(self, crates_data):
        x_coords = []
        y_coords = []
        colors = []
        for entry in crates_data:
            x_coords.append(entry['origin'][0])
            y_coords.append(entry['origin'][1])
            if entry['scales'][0] <= 0.5:
                colors.append('blue')
            elif entry['initial_spawn_time_override'] > 0:
                colors.append('green')
            else:
                colors.append('#cc5500')  # burnt orange

        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Vent access required', markerfacecolor='blue', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Mid-Boss Crate (spawns after 10 minutes)', markerfacecolor='green', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Normal Crate', markerfacecolor='#cc5500', markersize=10),
        ]

        return self._create_plot(x_coords, y_coords, colors, legend_elements, 'midtown_crate')

    @staticmethod
    def _create_plot(x_coords, y_coords, colors, legend_elements, plot_id):
        fig = plt.figure(num=plot_id, figsize=(20, 20))

        # Extracted from Deadlock/game/citadel/pak01_dir.vpk:materials/minimap/dl_midtown.vmat_c
        img = plt.imread(os.path.join(os.path.dirname(__file__), 'minimap_midtown_mid_opaque.png'))

        scale = 10750.0
        plt.imshow(img, extent=(-scale, scale, -scale, scale))

        plt.scatter(x_coords, y_coords, s=20, c=colors, alpha=1)

        plt.legend(handles=legend_elements, loc='upper left', fontsize='xx-large', framealpha=1)

        plt.axis('off')

        plt.xlim(-10000, 10000)
        plt.ylim(-10000, 10000)

        # plt.savefig(filename, bbox_inches="tight", pad_inches=0)

        return fig

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
