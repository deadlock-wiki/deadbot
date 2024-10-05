import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource
import utils.json_utils as json_utils


# extends Resource
class Localization(resource.Resource):
    objects = {}

    def __init__(self, key):
        self.Key = key
        self.Data = {}

        Localization.objects[key] = self

    # Override save, load, and store such that
    # 1: localization objects output content of Key and Data, and not the actual attribute name
    # 2: objects are output to a localizations folder with the object key as the file name
    @classmethod
    def save_objects(cls, free_memory=True):
        localization_path = os.path.join(cls.resource_path, 'localizations')
        for lang, lang_obj in cls.objects.items():
            json_utils.write(os.path.join(localization_path, lang + '.json'), lang_obj.Data)

        if free_memory:
            cls.objects = {}

    @classmethod
    def load_objects(cls):
        localization_path = os.path.join(cls.resource_path, 'localizations')
        os.makedirs(localization_path, exist_ok=True)

        for file in os.listdir(localization_path):
            if file.endswith('.json'):
                file_name = file.split('.')[0]
                cls.objects[file_name] = json_utils.read(
                    os.path.join(localization_path, file_name + '.json')
                )

    @classmethod
    def store_resources(cls, hash):
        for lang, lang_data in hash.items():
            lang_obj = cls(lang)
            lang_obj.Data = lang_data
