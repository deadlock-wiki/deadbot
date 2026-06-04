import functools
from os import PathLike
from PIL import Image, ImageDraw, ImageFont


@functools.cache
def load_image(image_path: PathLike | str) -> Image.Image:
    """Loads and caches an image from the given path."""
    return Image.open(image_path).convert('RGBA')


def create_circle_marker(color: str, diameter: int = 20) -> Image.Image:
    """Creates a circular RGBA marker image of the given color."""
    img = Image.new('RGBA', (diameter, diameter), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, diameter - 1, diameter - 1), fill=color)
    return img


class MapPlotter:
    """
    Handles compositing markers and legends onto a base map image using Pillow
    """

    # The map coordinate extents (from the original matplotlib extent)
    MAP_EXTENT = 10750.0
    MAP_CLIP = 10000.0
    OUTPUT_SIZE = 2000  # Output image resolution (square)

    def __init__(self, base_map_path: PathLike | str):
        base = load_image(base_map_path)
        self.canvas = base.resize((self.OUTPUT_SIZE, self.OUTPUT_SIZE), Image.LANCZOS).copy()

    def _world_to_pixel(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to pixel coordinates on the output image."""
        half = self.OUTPUT_SIZE / 2
        scale = half / self.MAP_EXTENT  # Use full extent, not clip
        px = int(half + x * scale)
        py = int(half - y * scale)
        return px, py

    def place_circle_markers(
        self,
        x_coords: list[float],
        y_coords: list[float],
        colors: list[str],
        diameter: int = 14,
    ) -> None:
        """Paste circle markers at the given world coordinates."""
        for x, y, color in zip(x_coords, y_coords, colors):
            marker = create_circle_marker(color, diameter)
            px, py = self._world_to_pixel(x, y)
            offset = diameter // 2
            self.canvas.paste(marker, (px - offset, py - offset), marker)

    def place_image_markers(
        self,
        x_coords: list[float],
        y_coords: list[float],
        image_paths: list[PathLike | str],
        size: float = 0.06,  # Fraction of output image width
    ) -> None:
        """Paste image markers at the given world coordinates."""
        icon_size = int(self.OUTPUT_SIZE * size)
        for x, y, path in zip(x_coords, y_coords, image_paths):
            icon = load_image(path).resize((icon_size, icon_size), Image.LANCZOS)
            px, py = self._world_to_pixel(x, y)
            offset = icon_size // 2
            self.canvas.paste(icon, (px - offset, py - offset), icon)

    def add_circle_legend(
        self,
        entries: list[tuple[str, str]],  # [(label, color), ...]
        font_size: int = 28,
        marker_diameter: int = 20,
        padding: int = 16,
    ) -> None:
        """Render a simple circle-icon legend in the top-left corner."""
        draw = ImageDraw.Draw(self.canvas)
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size)
        except OSError:
            font = ImageFont.load_default()

        row_height = marker_diameter + padding
        legend_height = row_height * len(entries) + padding
        # Estimate max label width
        max_label_width = max(draw.textlength(label, font=font) for label, _ in entries)
        legend_width = int(marker_diameter + padding + max_label_width + padding * 2)

        # Draw background
        draw.rectangle((padding, padding, padding + legend_width, padding + legend_height), fill=(255, 255, 255, 220))

        for i, (label, color) in enumerate(entries):
            y_top = padding * 2 + i * row_height
            # Circle
            draw.ellipse(
                (padding * 2, y_top, padding * 2 + marker_diameter, y_top + marker_diameter),
                fill=color,
            )
            # Label
            draw.text(
                (padding * 2 + marker_diameter + padding, y_top),
                label,
                fill=(0, 0, 0, 255),
                font=font,
            )

    def add_image_legend(
        self,
        entries: list[tuple[str, PathLike | str]],  # [(label, image_path), ...]
        icon_size: int = 36,
        font_size: int = 28,
        padding: int = 16,
    ) -> None:
        """Render a legend with image icons in the top-left corner."""
        draw = ImageDraw.Draw(self.canvas)
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', font_size)
        except OSError:
            font = ImageFont.load_default()

        row_height = icon_size + padding
        legend_height = row_height * len(entries) + padding
        max_label_width = max(draw.textlength(label, font=font) for label, _ in entries)
        legend_width = int(icon_size + padding + max_label_width + padding * 2)

        draw.rectangle((padding, padding, padding + legend_width, padding + legend_height), fill=(255, 255, 255, 220))

        for i, (label, img_path) in enumerate(entries):
            y_top = padding * 2 + i * row_height
            icon = load_image(img_path).resize((icon_size, icon_size), Image.LANCZOS)
            self.canvas.paste(icon, (padding * 2, y_top), icon)
            draw.text(
                (padding * 2 + icon_size + padding, y_top + (icon_size - font_size) // 2),
                label,
                fill=(0, 0, 0, 255),
                font=font,
            )

    def get_image(self) -> Image.Image:
        return self.canvas
