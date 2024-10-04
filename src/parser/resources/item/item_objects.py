import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource


# extends Resource
class Item(resource.Resource):
    objects = {}
    chart = None

    def __init__(self, key):
        self.key = key
        self.data = {}

        Item.objects[key] = self

    @classmethod
    def save_chart(cls):
        with open(cls.output_path + '/item-component-tree.txt', 'w') as f:
            f.write(str(cls.chart))
