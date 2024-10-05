import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource


# extends Resource
class Item(resource.Resource):
    objects = {}
    chart = None

    def __init__(self, key):
        self.Key = key
        self.Name = ''
        self.Description = ''
        self.Cost = ''
        self.Tier = ''
        self.Activation = ''
        self.Slot = ''
        self.Components = []
        self.TargetTypes = []
        self.ShopFilters = []
        self.Disabled = True
        self.Data = {}

        Item.objects[key] = self

    @classmethod
    def save_chart(cls):
        with open(cls.output_path + '/item-component-tree.txt', 'w') as f:
            f.write(str(cls.chart))
