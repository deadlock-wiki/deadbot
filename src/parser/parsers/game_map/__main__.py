import json
import os
from os import PathLike

from typing import TypedDict, Any

from PIL import Image
from utils.plot_utils import MapPlotter
from utils.process import run_process


class GameMapData(TypedDict):
    plots: dict[str, Image.Image]  # was plt.Figure
    metadata: dict[str, Any]


class _EntityData(TypedDict):
    origin: list[float]


class _BreakablesData(_EntityData):
    scales: list[float]
    initial_spawn_time_override: float


class GameMapParser:
    """Parse the Deadlock map for relevant wiki data"""

    def __init__(self, game_map_path: PathLike | str):
        """
        Initialize a GameMapParser for the midtown map
        Args:
            game_map_path: Path to the game map file
        """
        if not os.path.exists(game_map_path):
            raise FileNotFoundError(f'Could not find game map at path "{game_map_path}". Run with --import_files to download the map')

        self.entity_helper_cmd = os.getenv('ENTITY_HELPER_CMD', 'tools/DeadlockEntityHelper')
        self.game_map_path = game_map_path

    def run(self) -> dict[str, GameMapData]:
        """
        Parse the game map
        Returns:
            A dict containing the plots and metadata for the Midtown map
        """
        midtown_crates_data, midtown_statues_data = self._get_breakables_data()
        midtown_shop_data = self._get_shop_data()

        midtown_crate_plot = self._midtown_crate_plot(midtown_crates_data)
        midtown_statues_plot = self._midtown_golden_statues_plot(midtown_statues_data)
        midtown_shop_plot = self._midtown_shop_plot(midtown_shop_data)

        midtown_metadata = {'golden_statues_count': len(midtown_statues_data), 'crate_count': len(midtown_crates_data)}

        return {
            'midtown': {
                'plots': {
                    'crate': midtown_crate_plot,
                    'golden_statues': midtown_statues_plot,
                    'shops': midtown_shop_plot,
                },
                'metadata': midtown_metadata,
            }
        }

    def _midtown_golden_statues_plot(self, statues_data: list[_BreakablesData]) -> Image.Image:
        glitched_statues = [[-704, -2320.0002, 704], [704, 2320.0002, 704], [3647.9998, 1440.0004, 1048.0]]
        x_coords, y_coords, colors = [], [], []
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

        legend = [
            ('Vent access required', 'blue'),
            ('T2 Statue (spawns after 10 minutes)', 'green'),
            ('Glitched Statue', 'red'),
            ('Normal Statue', 'orange'),
        ]
        return self._create_circle_plot(x_coords, y_coords, colors, legend)

    def _midtown_crate_plot(self, crates_data: list[_BreakablesData]) -> Image.Image:
        glitched_crates = [[-7158.9175, -6115.6543, 640]]
        x_coords, y_coords, colors = [], [], []
        for entry in crates_data:
            x_coords.append(entry['origin'][0])
            y_coords.append(entry['origin'][1])
            if entry['origin'] in glitched_crates:
                colors.append('#F52D9C')
            elif entry['scales'][0] <= 0.5:
                colors.append('blue')
            elif entry['initial_spawn_time_override'] > 0:
                colors.append('green')
            else:
                colors.append('#cc5500')

        legend = [
            ('Vent access required', 'blue'),
            ('Glitched Crate', '#F52D9C'),
            ('Mid-Boss Crate (spawns after 10 minutes)', 'green'),
            ('Normal Crate', '#cc5500'),
        ]
        return self._create_circle_plot(x_coords, y_coords, colors, legend)

    def _midtown_shop_plot(self, shop_data: list[_EntityData]) -> Image.Image:
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        x_coords, y_coords, image_paths = [], [], []
        for entry in shop_data:
            x_coords.append(entry['origin'][0])
            y_coords.append(entry['origin'][1])
            if entry['origin'][2] < 0:
                image_paths.append(os.path.join(assets_dir, 'minimap_shop_psd.png'))
            elif entry['origin'][1] < 0:
                image_paths.append(os.path.join(assets_dir, 'minimap_shop_psd_hidden_king.png'))
            else:
                image_paths.append(os.path.join(assets_dir, 'minimap_shop_psd_archmother.png'))

        legend = [
            ('Hidden King', os.path.join(assets_dir, 'minimap_shop_psd_hidden_king.png')),
            ('Archmother', os.path.join(assets_dir, 'minimap_shop_psd_archmother.png')),
            ('Secret Shop', os.path.join(assets_dir, 'minimap_shop_psd.png')),
        ]
        return self._create_image_plot(x_coords, y_coords, image_paths, legend)

    def _create_circle_plot(
        self,
        x_coords: list[float],
        y_coords: list[float],
        colors: list[str],
        legend: list[tuple[str, str]],
    ) -> Image.Image:
        base_map = os.path.join(os.path.dirname(__file__), 'assets/minimap_midtown_mid_opaque.png')
        plotter = MapPlotter(base_map)
        plotter.place_circle_markers(x_coords, y_coords, colors, diameter=10)
        plotter.add_circle_legend(legend)
        return plotter.get_image()

    def _create_image_plot(
        self,
        x_coords: list[float],
        y_coords: list[float],
        image_paths: list[str],
        legend: list[tuple[str, str]],
    ) -> Image.Image:
        base_map = os.path.join(os.path.dirname(__file__), 'assets/minimap_midtown_mid_opaque.png')
        plotter = MapPlotter(base_map)
        plotter.place_image_markers(x_coords, y_coords, image_paths, size=0.035)
        plotter.add_image_legend(legend)
        return plotter.get_image()

    def _get_shop_data(self) -> list[_EntityData]:
        """
        Extract shop entities from the map
        Returns:
            A list of shop entities
        """
        shop_trigger_properties = [
            'origin',
            'vector3',
        ]

        shop_data: list[_EntityData] = self._extract_entities('classname', 'citadel_shop_prop_dynamic', *shop_trigger_properties)

        # Hardcoded base shops because there is no actual base shop
        #   it's a longer story than that, but this is easier to explain than using unrelated entities
        # PyCharm's linter cannot type-check this for some reason
        # noinspection PyTypeChecker
        shop_data.extend([{'origin': [0, -9500, 100]}, {'origin': [0, -9500, 100]}])
        return shop_data

    def _get_breakables_data(self) -> tuple[list[_BreakablesData], ...]:
        """
        Extract breakable entities from the map
        Returns:
            A list of breakable entities
        """
        breakables_properties = [
            'initial_spawn_time_override',
            'double',  # Used to identify breakables that are spawned late
            'scales',
            'vector3',  # Scale of the breakable
            'origin',
            'vector3',  # Position on the map
        ]

        return (
            self._extract_entities('subclass_name', 'citadel_breakable_prop_wooden_crate', *breakables_properties),
            self._extract_entities('subclass_name', 'citadel_breakable_item_container', *breakables_properties),
        )

    def _extract_entities(self, entity_key, entity_value, *property_list) -> list[Any]:
        """
        Runs `DeadlockEntityHelper extract` with the specified arguments
        :param property_list: the remaining args are treated as property name-type pairs, e.g.:
            `_extract_entities('citadel_breakable_prop_wooden_crate', 'origin', 'vector3', 'subclass_name', 'string')`
        :return: a list of entities with the requested properties
        """
        args = [self.entity_helper_cmd, 'extract', '--verbose', '--compact', self.game_map_path, entity_key, entity_value, *property_list]
        helper_output = run_process(args, 'extract-map-entities', suppress_stdout=True)
        return json.loads(helper_output)
