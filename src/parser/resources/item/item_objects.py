import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource

# extends Resource
class Item (resource.Resource):
    objects = {}

    def __init__(self, key):
        self.Key = key
        self.Name = ""
        self.Description = ""
        self.Cost = ""
        self.Tier = ""
        self.Activation = ""
        self.Slot = ""
        self.Components = ""
        self.TargetTypes = []
        self.ShopFilters = []
        self.Cooldown = 0.0
        self.Duration = ""
        self.CastRange = ""
        self.UnitTargetLimit = ""
        self.CastDelay = ""
        self.ChannelTime = ""
        self.PostCastDuration = ""
        self.Charges = ""
        self.CooldownBetweenCharge = ""
        self.ChannelMoveSpeed = ""
        self.ResourceCost = ""
        self.TechPower = ""
        self.WeaponPower = ""
        self.TempTechShieldHealth = ""
        self.Radius = ""
        self.Disabled = True

        Item.objects[key] = self
    