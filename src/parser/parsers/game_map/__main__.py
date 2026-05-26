import json
import os
from os import PathLike

from typing import TypedDict, Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

from utils.plot_utils import ImageHandler, load_image
from utils.process import run_process


class GameMapData(TypedDict):
    plots: dict[str, plt.Figure]
    metadata: dict[str, Any]


class _EntityData(TypedDict):
    origin: list[float]


class _BreakablesData(_EntityData):
    scales: list[float]
    initial_spawn_time_override: float


class GameMapParser:
    """Parse the Deadlock map for relevant wiki data"""

    def __init__(self, entity_helper_cmd: PathLike | str, game_map_path: PathLike | str):
        """
        Initialize a GameMapParser for the midtown map
        Args:
            entity_helper_cmd: Path to the DeadlockEntityHelper executable
            game_map_path: Path to the game map file
        """
        if not entity_helper_cmd:
            raise ValueError('Config for DeadlockEntityHelper path is required for game map parsing')
        if not os.path.exists(entity_helper_cmd):
            raise FileNotFoundError(f'Could not find DeadlockEntityHelper at path "{entity_helper_cmd}"')
        if not os.path.exists(game_map_path):
            raise FileNotFoundError(f'Could not find game map at path "{game_map_path}". Run with --import_files to download the map')

        self.entity_helper_cmd = entity_helper_cmd
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

    def _midtown_golden_statues_plot(self, statues_data: list[_BreakablesData]) -> plt.Figure:
        """
        Generate a plot of the midtown golden statues
        Args:
            statues_data: The data for the golden statues from DeadlockEntityHelper
        Returns:
            The plot of the midtown golden statues
        """
        # These should be hard-coded exact coords, because if they ever change, they are probably not glitched anymore
        glitched_statues = [[-704, -2320.0002, 704], [704, 2320.0002, 704], [3647.9998, 1440.0004, 1048.0]]

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

        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Vent access required', markerfacecolor='blue', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='T2 Statue (spawns after 10 minutes)', markerfacecolor='green', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Glitched Statue', markerfacecolor='red', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Normal Statue', markerfacecolor='orange', markersize=10),
        ]

        return self._create_plot(x_coords, y_coords, colors, None, legend_elements, 'midtown_golden_statues')

    def _midtown_crate_plot(self, crates_data: list[_BreakablesData]) -> plt.Figure:
        """
        Generate a plot of the midtown crates
        Args:
            crates_data: The data for the crates from DeadlockEntityHelper
        Returns:
            The plot of the midtown crates
        """
        glitched_crates = [[-7158.9175, -6115.6543, 640]]
        x_coords = []
        y_coords = []
        colors = []
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
                colors.append('#cc5500')  # burnt orange

        legend_elements = [
            Line2D([0], [0], marker='o', color='w', label='Vent access required', markerfacecolor='blue', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Glitched Crate', markerfacecolor='#F52D9C', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Mid-Boss Crate (spawns after 10 minutes)', markerfacecolor='green', markersize=10),
            Line2D([0], [0], marker='o', color='w', label='Normal Crate', markerfacecolor='#cc5500', markersize=10),
        ]

        return self._create_plot(x_coords, y_coords, colors, None, legend_elements, 'midtown_crate')

    def _midtown_shop_plot(self, shop_data: list[_EntityData]) -> plt.Figure:
        """
        Generate a plot of the midtown shops
        Args:
            shop_data: The data for the shops from DeadlockEntityHelper
        Returns:
            The plot of the midtown shops
        """
        x_coords = []
        y_coords = []
        image_paths = []
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        for entry in shop_data:
            x_coords.append(entry['origin'][0])
            y_coords.append(entry['origin'][1])
            if entry['origin'][2] < 0:
                image_paths.append(os.path.join(assets_dir, 'minimap_shop_psd.png'))
            elif entry['origin'][1] < 0:
                image_paths.append(os.path.join(assets_dir, 'minimap_shop_psd_hidden_king.png'))
            else:
                image_paths.append(os.path.join(assets_dir, 'minimap_shop_psd_archmother.png'))

        legend_info = {
            'Hidden King': os.path.join(assets_dir, 'minimap_shop_psd_hidden_king.png'),
            'Archmother': os.path.join(assets_dir, 'minimap_shop_psd_archmother.png'),
            'Secret Shop': os.path.join(assets_dir, 'minimap_shop_psd.png'),
        }
        legend_elements = [Line2D(label=label, xdata=[0], ydata=[0]) for label in legend_info.keys()]
        # element.get_label() is annotated as returning an object which causes a warning,
        # but in this case we are sure it is a string since we just set it above
        # noinspection PyTypeChecker
        handler_map = {element: ImageHandler(legend_info[element.get_label()], size=0.9) for element in legend_elements}

        return self._create_plot(x_coords, y_coords, None, image_paths, legend_elements, 'midtown_shops', size=1.2, handler_map=handler_map)

    @staticmethod
    def _create_plot(
        x_coords: list[float],
        y_coords: list[float],
        colors: list[str] | None,
        markers: list[PathLike | str] | None,
        legend_elements: list[Line2D],
        plot_id: str,
        size: float = 20.0,
        handler_map: dict[Line2D, ImageHandler] = None,
        **kwargs,
    ) -> plt.Figure:
        """
        Plots the given coordinates onto the midtown map
        Parameters:
            x_coords: The x coordinates of the points to plot
            y_coords: The y coordinates of the points to plot
            colors: A list of colors for the points. If `None`, markers should be provided
            markers: A list of file paths pointing to marker images to be displayed
            legend_elements: A list of `Line2D` objects to display in the plot's legend
            plot_id: A unique identifier for the plot
            size: A multiplier for the size of points or markers in the plot
            handler_map: If you want legend icons to be images, this should be a map of your `Line2D` legend elements
                to `utils.plot_utils.ImageHandler` objects (see `GameMapParser._midtown_shop_plot` for an example)
            **kwargs: Additional keyword arguments are passed to the `matplotlib.pyploy.scatter` function.
                This is unused if `markers` are provided
        Returns:
            The generated plot
        """
        fig = plt.figure(num=plot_id, figsize=(20, 20))

        # Extracted from Deadlock/game/citadel/pak01_dir.vpk:materials/minimap/dl_midtown.vmat_c
        img = load_image(os.path.join(os.path.dirname(__file__), 'assets/minimap_midtown_mid_opaque.png'))

        scale = 10750.0
        plt.imshow(img, extent=(-scale, scale, -scale, scale))

        if colors is not None:
            plt.scatter(x_coords, y_coords, s=size, c=colors, alpha=1, **kwargs)
        else:
            axes = plt.gca()
            for x, y, img_path in zip(x_coords, y_coords, markers):
                image = load_image(img_path)
                image_box = OffsetImage(image, zoom=size)
                ab = AnnotationBbox(image_box, (x, y), frameon=False)
                axes.add_artist(ab)

        plt.legend(handles=legend_elements, loc='upper left', fontsize='xx-large', framealpha=1, handler_map=handler_map)

        plt.axis('off')

        plt.xlim(-10000, 10000)
        plt.ylim(-10000, 10000)

        return fig

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
