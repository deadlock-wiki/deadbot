import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource

# extends Resource
class Item (resource.Resource):
    objects = {}

    def __init__(self, key):
        self.key = key
        self.data = {}

        Item.objects[key] = self