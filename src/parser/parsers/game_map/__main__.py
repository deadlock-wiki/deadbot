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


class _Breakable(TypedDict):
    entity_class: str
    label: str
    color: str


# Plot name -> the map entity it plots. The plot name is also the output file stem, e.g. crate_map.png
BREAKABLES: dict[str, _Breakable] = {
    'crate': {
        'entity_class': 'citadel_breakable_prop_wooden_crate',
        'label': 'Crate',
        'color': '#1e90ff',
    },
    'golden_statues': {
        # Valve's name for these is "golden statue", players call them buff containers
        'entity_class': 'citadel_breakable_item_container',
        'label': 'Buff containers',
        'color': '#ffd700',
    },
    'heavy_crate': {
        'entity_class': 'citadel_breakable_prop_tough_crate',
        'label': 'Heavy crate',
        'color': '#22c55e',
    },
    'healing_snack': {
        # Not a breakable, but a pickup spawner that re-spawns the snack on a timer
        'entity_class': 'citadel_pickup_floating_health',
        'label': 'Healing Snack',
        'color': '#ec4899',
    },
}

# The current Midtown minimap, regenerated with scripts/update_minimap.py
BREAKABLES_BASE_MAP = os.path.join(os.path.dirname(__file__), 'assets/minimap_midtown.png')


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
        positions = {name: self._get_positions(spec['entity_class']) for name, spec in BREAKABLES.items()}

        plots = {name: self._breakables_plot({name: coords}) for name, coords in positions.items()}
        # Every category on one map
        plots['breakables'] = self._breakables_plot(positions)
        plots['shops'] = self._midtown_shop_plot(self._get_shop_data())

        return {
            'midtown': {
                'plots': plots,
                'metadata': {f'{name}_count': len(coords) for name, coords in positions.items()},
            }
        }

    def _breakables_plot(self, positions: dict[str, list[tuple[float, float]]]) -> Image.Image:
        """
        Plot one dot per position onto the midtown map at its native resolution, with a legend counting each category
        Args:
            positions: Breakable name (a key of BREAKABLES) -> world (x, y) positions
        Returns:
            The generated plot
        """
        plotter = MapPlotter(BREAKABLES_BASE_MAP, output_size=None)
        for name in sorted(positions):
            plotter.place_dots(positions[name], BREAKABLES[name]['color'])

        total = sum(len(coords) for coords in positions.values())
        title = f'main   {plotter.output_size}x{plotter.output_size}   markers={total}'
        legend = [
            (f'{BREAKABLES[name]["label"]}  ({len(positions[name])})', BREAKABLES[name]['color']) for name in sorted(positions) if positions[name]
        ]
        plotter.add_compact_legend(title, legend)
        return plotter.get_image()

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

    def _create_image_plot(
        self,
        x_coords: list[float],
        y_coords: list[float],
        image_paths: list[str],
        legend: list[tuple[str, str]],
    ) -> Image.Image:
        """
        Plots the given images onto the midtown map
        Parameters:
            x_coords: The x coordinates of the points to plot
            y_coords: The y coordinates of the points to plot
            image_paths: List of image paths to read and plot
            legend: A list of label and colour pairs to display in the plot's legend
        Returns:
            The generated plot
        """
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
        shop_data.extend(
            [
                {'origin': [0, -9500, 100]},  # Hidden King base shop
                {'origin': [0, 9500, 100]},  # Archmother base shop
            ]
        )
        return shop_data

    def _get_positions(self, entity_class: str) -> list[tuple[float, float]]:
        """
        Extract the world (x, y) position of every entity of the given class from the map
        """
        entities: list[_EntityData] = self._extract_entities('subclass_name', entity_class, 'origin', 'vector3')
        return [(entity['origin'][0], entity['origin'][1]) for entity in entities if entity.get('origin')]

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
