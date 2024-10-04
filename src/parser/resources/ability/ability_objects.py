import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource

# extends Resource
class Ability (resource.Resource):
    objects = {}

    def __init__(self, key):
        self.key = key
        self.data = {}

        Ability.objects[key] = self

class AbilityUI (resource.Resource):
    objects = {}

    def __init__(self, key):
        self.key = key
        self.data = {}

        AbilityUI.objects[key] = self