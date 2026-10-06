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


# Bold fonts first. Covers the Linux docker image and local Windows runs
LEGEND_FONTS = (
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    'C:/Windows/Fonts/segoeuib.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
)


def _load_font(paths: tuple[str, ...], size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Returns the first font that loads from `paths`, falling back to Pillow's built-in font."""
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


class MapPlotter:
    """
    Handles compositing markers and legends onto a base map image using Pillow
    """

    # The map coordinate extents (from the original matplotlib extent)
    MAP_EXTENT = 10750.0
    MAP_CLIP = 10000.0
    OUTPUT_SIZE = 2000  # Output image resolution (square)

    def __init__(self, base_map_path: PathLike | str, output_size: int | None = OUTPUT_SIZE):
        """
        Args:
            base_map_path: Path to the square base map image
            output_size: Resolution to resample the base map to. `None` keeps its native resolution
        """
        base = load_image(base_map_path)
        self.output_size = output_size or base.width
        self.canvas = base.resize((self.output_size, self.output_size), Image.LANCZOS).copy()

    def _world_to_pixel(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to pixel coordinates on the output image."""
        half = self.output_size / 2
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
        icon_size = int(self.output_size * size)
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

    def place_dots(self, coords: list[tuple[float, float]], color: str, radius: float = 3.45) -> None:
        """Draw a solid dot at each world coordinate, at sub-pixel precision."""
        draw = ImageDraw.Draw(self.canvas)
        half = self.output_size / 2
        scale = half / self.MAP_EXTENT
        for x, y in coords:
            px = half + x * scale
            py = half - y * scale
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)

    def add_compact_legend(
        self,
        title: str,
        entries: list[tuple[str, str]],  # [(label, color), ...]
        font_size: int = 10,
        swatch_size: int = 7,
        padding: int = 5,
    ) -> None:
        """Render a small dark legend in the top-left corner: a title row, then one swatch per entry."""
        rows = [(None, title)] + [(color, label) for label, color in entries]
        overlay = Image.new('RGBA', self.canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = _load_font(LEGEND_FONTS, font_size)

        text_width = max(draw.textlength(text, font=font) for _, text in rows)
        row_height = font_size + padding
        box_width = int(swatch_size + 2 * padding + text_width + padding)
        box_height = int(row_height * len(rows) + padding)
        draw.rectangle((padding, padding, padding + box_width, padding + box_height), fill=(0, 0, 0, 255))

        # Pillow anchors text by its ascender, so nudge rows up slightly to sit level with the swatch
        text_dy = int(font_size * -0.15)
        swatch_dy = int(font_size * -0.08)
        gap = max(2, int(font_size * 0.4))
        for i, (color, text) in enumerate(rows):
            x = padding * 2
            y = padding * 2 + i * row_height
            if color is None:
                draw.text((x, y + text_dy), text, fill=(255, 255, 255, 255), font=font)
                continue
            draw.ellipse((x, y + swatch_dy, x + swatch_size, y + swatch_dy + swatch_size), fill=color, outline=(255, 255, 255, 255))
            draw.text((x + swatch_size + gap, y + text_dy), text, fill=(255, 255, 255, 255), font=font)

        self.canvas = Image.alpha_composite(self.canvas, overlay)

    def get_image(self) -> Image.Image:
        return self.canvas
