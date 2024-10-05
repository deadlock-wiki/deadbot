import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource


# extends Resource
class Changelog(resource.Resource):
    objects = {}

    # changelog restructure will require most of this to change, 
    # these attributes are placeholders
    def __init__(self, key):
        self.Key = key
        self.Heroes = {}
        self.Items = {}
        self.Abilities = {}
        self.General = {}
        self.Other = {}
        self.Misc = {}
        self.Map = {}
        self.Data = {}

        Changelog.objects[key] = self
