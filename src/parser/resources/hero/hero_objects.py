import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource


# extends Resource
class Hero(resource.Resource):
    objects = {}

    def __init__(self, key):
        self.Key = key
        self.Name = ''
        self.LevelScaling = {}
        self.SpiritScaling = {}
        self.Lore = ''
        self.Role = ''
        self.Playstyle = ''
        self.BoundAbilities = []

        self.InDevelopment = None
        self.IsDisabled = None

        self.Data = {}

        Hero.objects[key] = self
