import functools
from os import PathLike

from matplotlib.legend_handler import HandlerBase
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image


class ImageHandler(HandlerBase):
    """This adds support for images in a chart's legend"""

    def __init__(self, image_path: PathLike | str, size: float = 1.0):
        """
        Initializes the ImageHandler with the given image path and size

        Args:
            image_path: The path to the image file
            size: The size of the image in the legend
        """
        super().__init__()
        self.image_path = image_path
        self.size = size

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        """
        Override for `HandlerBase.create_artists` to embed an image in the legend
        See `HandlerBase.create_artists` for more details
        """
        image = load_image(self.image_path)
        image_box = OffsetImage(image, zoom=self.size)
        # Center the image and apply the given transform
        annotation_box = AnnotationBbox(image_box, (width / 2, height / 2), xycoords=trans, frameon=False)
        return [annotation_box]


@functools.cache
def load_image(image_path: PathLike | str):
    """Loads an image from the given path. Memoized to avoid reloading the same image"""
    # Cached to avoid reloading the same images
    return Image.open(image_path)
