import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import utils.json_utils as json_utils
import resources.resource as resource

# extends Resource
class Attribute (resource.Resource):
    objects = {}
    order_lists = {}
    meaningful_stats = {}

    def __init__(self, key):
        self.key = key
        self.data = {}

        Attribute.objects[key] = self

    @classmethod
    def save_meaningful_stats(cls):
        path = cls.output_path + '/meaningful-stats.json'
        # Ensure it matches the current list of meaningful stats, and raise a warning if not
        # File diff will also appear in git
        if os.path.exists and not json_utils.compare_json_file_to_dict(path, cls.meaningful_stats):
            print(
                'Warning: Non-constant stats have changed. '
                + "Please update [[Module:HeroData]]'s write_hero_comparison_table "
                + 'lua function for the [[Hero Comparison]] page.'
            )

        json_utils.write(path, cls.meaningful_stats)

    @classmethod
    def save_order_lists(cls):
        json_utils.write(cls.output_path+'/stat-infobox-order.json', cls.order_lists)