import functools

from matplotlib.legend_handler import HandlerBase
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image


class ImageHandler(HandlerBase):
    """This adds support for images in a chart's legend"""

    def __init__(self, image_path, size=1.0):
        super().__init__()
        self.image_path = image_path
        self.size = size

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        image = load_image(self.image_path)
        image_box = OffsetImage(image, zoom=self.size)
        # Center the image and apply the given transform
        annotation_box = AnnotationBbox(image_box, (width / 2, height / 2), xycoords=trans, frameon=False)
        return [annotation_box]


@functools.cache
def load_image(image_path):
    # Cached to avoid reloading the same images
    return Image.open(image_path)
