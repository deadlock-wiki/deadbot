import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource


# extends Resource
class Ability(resource.Resource):
    objects = {}

    def __init__(self, key):
        self.Key = key
        self.Name = ''
        self.Upgrades = []
        self.Data = {}

        Ability.objects[key] = self


class AbilityUI(resource.Resource):
    objects = {}

    def __init__(self, key):
        self.Key = key
        self.Name = ''
        self.Data = {}

        AbilityUI.objects[key] = self
