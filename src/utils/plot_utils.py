import functools
from os import PathLike
from PIL import Image, ImageDraw, ImageFont


@functools.cache
def load_image(image_path: PathLike | str) -> Image.Image:
    """Loads and caches an image from the given path."""
    return Image.open(image_path).convert('RGBA')


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

    def _world_to_pixel(self, x: float, y: float) -> tuple[float, float]:
        """Convert world coordinates to sub-pixel coordinates on the output image."""
        half = self.output_size / 2
        scale = half / self.MAP_EXTENT  # Use full extent, not clip
        px = half + x * scale
        py = half - y * scale
        return px, py

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
            px, py = map(int, self._world_to_pixel(x, y))
            offset = icon_size // 2
            self.canvas.paste(icon, (px - offset, py - offset), icon)

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

    def place_dots(
        self,
        coords: list[tuple[float, float]],
        color: str,
        radius: float = 3.45,
        outline: str = 'black',
        outline_width: int = 1,
    ) -> None:
        """Draw an outlined dot at each world coordinate, at sub-pixel precision, so overlapping dots stay distinct."""
        draw = ImageDraw.Draw(self.canvas)
        # Pillow draws the outline inside the bounding box, so grow it to keep the fill at `radius`
        r = radius + outline_width
        for x, y in coords:
            px, py = self._world_to_pixel(x, y)
            draw.ellipse((px - r, py - r, px + r, py + r), fill=color, outline=outline, width=outline_width)

    def add_compact_legend(
        self,
        entries: list[tuple[str, str]],  # [(label, color), ...]
        title: str | None = None,
        font_size: int = 10,
        title_font_size: int = 16,
        swatch_size: int = 7,
        padding: int = 5,
    ) -> None:
        """Render a small dark legend in the top-left corner: an optional title, then one colour swatch and label per row."""
        overlay = Image.new('RGBA', self.canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = _load_font(LEGEND_FONTS, font_size)
        title_font = _load_font(LEGEND_FONTS, title_font_size)

        row_height = font_size + padding
        # The title, then a gap, a divider line and another gap before the first row
        title_height = title_font_size + padding * 3 if title else 0
        text_width = max(draw.textlength(label, font=font) for label, _ in entries)
        box_width = int(max(swatch_size + 2 * padding + text_width, draw.textlength(title, font=title_font) + padding if title else 0) + padding)
        box_height = int(title_height + row_height * len(entries) + padding)
        draw.rectangle((padding, padding, padding + box_width, padding + box_height), fill=(255, 255, 255, 255))

        # Pillow anchors text by its ascender, so nudge rows up slightly to sit level with the swatch
        text_dy = font_size * -0.4
        swatch_dy = 0
        # swatch_dy = int(font_size * -0.08)
        gap = max(2, int(font_size * 0.4))
        x = padding * 2
        if title:
            draw.text((x, padding * 2 + int(title_font_size * -0.15)), title, fill=(0, 0, 0, 255), font=title_font)
            divider_y = padding * 2 + title_font_size + padding
            draw.line((x, divider_y, padding + box_width - padding, divider_y), fill=(110, 110, 110, 255), width=1)
        for i, (label, color) in enumerate(entries):
            y = padding * 2 + title_height + i * row_height
            draw.ellipse((x, y + swatch_dy, x + swatch_size, y + swatch_dy + swatch_size), fill=color, outline=(0, 0, 0, 255))
            draw.text((x + swatch_size + gap, y + text_dy), label, fill=(0, 0, 0, 255), font=font)

        self.canvas = Image.alpha_composite(self.canvas, overlay)

    def get_image(self) -> Image.Image:
        return self.canvas
