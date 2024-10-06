import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource


# extends Resource
class Weapon(resource.Resource):
    objects = {}
    chart = None

    def __init__(self, key):
        self.Key = key
        self.Name = ''
        self.Description = ''
        self.Data = {}

        Weapon.objects[key] = self