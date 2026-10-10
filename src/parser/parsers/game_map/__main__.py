import json
import os
from os import PathLike

from collections import Counter
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
    title: str  # Map title when plotted alone
    # One colour per first spawn time, earliest first. Times come from the spawn groups in use, e.g. 3:00, 5:00, 10:00
    colors: list[str]


class _BreakableEntity(TypedDict):
    position: tuple[float, float]
    spawn_time: float | None  # Seconds into the match it first spawns, or None if it has no spawn group


BREAKABLES: dict[str, _Breakable] = {
    'crate': {
        'entity_class': 'citadel_breakable_prop_wooden_crate',
        'label': 'Crate',
        'title': 'Crates',
        'colors': ['#1e90ff', '#22d3ee', '#a855f7'],
    },
    'heavy_crate': {
        'entity_class': 'citadel_breakable_prop_tough_crate',
        'label': 'Heavy crate',
        'title': 'Heavy crates',
        'colors': ['#22c55e', '#bef264', '#ef4444'],
    },
    'golden_statues': {
        # Valve's name for these is "golden statue", players call them buff containers
        'entity_class': 'citadel_breakable_item_container',
        'label': 'Buff container',
        'title': 'Buff containers',
        'colors': ['#ffd700', '#f97316', '#ec4899'],
    },
    'healing_snack': {
        # Not a breakable, but a pickup spawner that re-spawns the snack on a timer
        'entity_class': 'citadel_pickup_floating_health',
        'label': 'Healing snack',
        'title': 'Healing snacks',
        'colors': ['#f5f5f5'],
    },
}

# Maps plotting several kinds together. Each kind also gets its own map, e.g. crate -> crate_map.png
# Output file stem -> (map title, the breakables plotted on it), e.g. all_crates -> all_crates_map.png
COMBINED_MAPS: dict[str, tuple[str, list[str]]] = {
    'all_crates': ('Crates and heavy crates', ['crate', 'heavy_crate']),
    'all_breakables': ('All breakables and healing snacks', list(BREAKABLES)),
}

# The current Midtown minimap, regenerated with scripts/update_minimap.py
BREAKABLES_BASE_MAP = os.path.join(os.path.dirname(__file__), 'assets/minimap_midtown_opaque.png')


class GameMapParser:
    """Parse the Deadlock map for relevant wiki data"""

    def __init__(self, game_map_path: PathLike | str, breakable_spawn_times: list[dict[str, float]]):
        """
        Initialize a GameMapParser for the midtown map
        Args:
            game_map_path: Path to the game map file
            breakable_spawn_times: m_BreakableSpawnTimeDesc from generic_data, indexed by each breakable's spawn group
        """
        if not os.path.exists(game_map_path):
            raise FileNotFoundError(f'Could not find game map at path "{game_map_path}". Run with --import_files to download the map')

        self.entity_helper_cmd = os.getenv('ENTITY_HELPER_CMD', 'tools/DeadlockEntityHelper')
        self.game_map_path = game_map_path
        self.breakable_spawn_times = breakable_spawn_times

    def run(self) -> dict[str, GameMapData]:
        """
        Parse the game map
        Returns:
            A dict containing the plots and metadata for the Midtown map
        """
        breakables = {name: self._get_breakables(spec['entity_class']) for name, spec in BREAKABLES.items()}
        # Colours are picked by spawn time order across every kind, so e.g. all 10:00 spawns use their kind's third colour
        spawn_order = sorted({e['spawn_time'] for entities in breakables.values() for e in entities if e['spawn_time'] is not None})

        plots = {name: self._breakables_plot({name: entities}, BREAKABLES[name]['title'], spawn_order) for name, entities in breakables.items()}
        plots |= {
            stem: self._breakables_plot({name: breakables[name] for name in names}, title, spawn_order)
            for stem, (title, names) in COMBINED_MAPS.items()
        }

        # One map per spawn time for each kind that spawns then, plus every kind together at that time, e.g. crate_5min, all_breakables_5min
        for spawn_time in spawn_order:
            at_time = {name: [e for e in entities if e['spawn_time'] == spawn_time] for name, entities in breakables.items()}
            at_time = {name: entities for name, entities in at_time.items() if entities}
            suffix = _format_minutes(spawn_time)
            for name, entities in at_time.items():
                plots[f'{name}_{suffix}'] = self._breakables_plot(
                    {name: entities}, f'{BREAKABLES[name]["title"]} spawning at {_format_time(spawn_time)}', spawn_order
                )
            plots[f'all_breakables_{suffix}'] = self._breakables_plot(at_time, f'All breakables spawning at {_format_time(spawn_time)}', spawn_order)

        plots['shops'] = self._midtown_shop_plot(self._get_shop_data())

        metadata = {}
        for name, entities in breakables.items():
            metadata[f'{name}_count'] = len(entities)
            spawn_counts = Counter(_format_time(e['spawn_time']) for e in entities if e['spawn_time'] is not None)
            if spawn_counts:
                metadata[f'{name}_spawn_counts'] = dict(spawn_counts)

        return {
            'midtown': {
                'plots': plots,
                'metadata': metadata,
            }
        }

    def _breakables_plot(self, breakables: dict[str, list[_BreakableEntity]], title: str, spawn_order: list[float]) -> Image.Image:
        """
        Plot one dot per breakable onto the midtown map at its native resolution, with a legend counting each kind.
        Each kind is split by when it first spawns, in its own colour
        Args:
            breakables: Breakable name (a key of BREAKABLES) -> its entities
            title: Shown above the legend, so the image says what it is
            spawn_order: Every first spawn time in use, earliest first. Picks each kind's colour for a spawn time
        Returns:
            The generated plot
        """
        series = []  # [(label, color, positions), ...]
        for name, entities in breakables.items():
            spec = BREAKABLES[name]
            spawn_times = sorted({e['spawn_time'] for e in entities}, key=lambda t: -1 if t is None else t)
            for spawn_time in spawn_times:
                positions = [e['position'] for e in entities if e['spawn_time'] == spawn_time]
                if spawn_time is None:
                    series.append((spec['label'], spec['colors'][0], positions))
                    continue
                color = spec['colors'][min(spawn_order.index(spawn_time), len(spec['colors']) - 1)]
                series.append((f'{spec["label"]}, spawns at {_format_time(spawn_time)}', color, positions))

        plotter = MapPlotter(BREAKABLES_BASE_MAP)
        for _, color, positions in series:
            plotter.place_dots(positions, color)
        plotter.add_compact_legend(
            [(f'{label} ({len(positions)})', color) for label, color, positions in series],
            title=title,
            font_size=26,
            title_font_size=32,
            padding=10,
            swatch_size=14,
        )
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
        base_map = BREAKABLES_BASE_MAP
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
                {'origin': [-1280.0, -10000.0, 100]},  # Hidden King base shop
                {'origin': [1280.0, 10000.0, 100]},  # Archmother base shop
            ]
        )
        return shop_data

    def _get_breakables(self, entity_class: str) -> list[_BreakableEntity]:
        """
        Extract every entity of the given class from the map, with its position and first spawn time
        """
        # The helper reads this integer as 0 when asked for a double, so read it as a string.
        # It's null for entities without a spawn group, e.g. healing snacks
        entities = self._extract_entities('subclass_name', entity_class, 'origin', 'vector3', 'breakable_spawn_group', 'string')
        return [
            {
                'position': (entity['origin'][0], entity['origin'][1]),
                'spawn_time': self._spawn_time(entity['breakable_spawn_group']),
            }
            for entity in entities
            if entity.get('origin')
        ]

    def _spawn_time(self, spawn_group: str | None) -> float | None:
        """Seconds into the match that a breakable in the given spawn group first spawns"""
        if spawn_group is None:
            return None
        return self.breakable_spawn_times[int(spawn_group)]['m_flInitialSpawnTime']

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


def map_file_stems(spawn_times: list[float]) -> list[str]:
    """
    Every map the parser can generate, as file stems, e.g. crate -> crate_map.png. A kind with nothing spawning
    at a given time gets no map for it, so not every stem is generated on every run
    Args:
        spawn_times: Each breakable spawn group's first spawn time in seconds, from BreakableSpawnTimeDesc in generic_data
    """
    stems = [*BREAKABLES, *COMBINED_MAPS, 'shops']
    for spawn_time in sorted(set(spawn_times)):
        suffix = _format_minutes(spawn_time)
        stems += [f'{name}_{suffix}' for name in BREAKABLES] + [f'all_breakables_{suffix}']
    return stems


def _format_time(seconds: float) -> str:
    """180 -> 3:00"""
    return f'{int(seconds // 60)}:{int(seconds % 60):02d}'


def _format_minutes(seconds: float) -> str:
    """300 -> 5min, for output file names"""
    return f'{int(seconds // 60)}min' if seconds % 60 == 0 else f'{int(seconds)}s'
