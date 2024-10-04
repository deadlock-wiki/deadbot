import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource

# extends Resource
class Item (resource.Resource):
    objects = {}
    chart = None

    def __init__(self, key):
        self.key = key
        self.data = {}

        Item.objects[key] = self

    @classmethod
    def set_chart(cls, chart):
        cls.chart = chart

    @classmethod
    def get_chart(cls):
        return cls.chart
    
    @classmethod
    def save_chart(cls):
        with open(cls.resource_path + '/item-component-tree.txt', 'w') as f:
            f.write(str(cls.chart))