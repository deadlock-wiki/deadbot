import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import resources.resource as resource
import utils.json_utils as json_utils


# extends Resource
class Localization(resource.Resource):
    objects = {}

    def __init__(self, key):
        self.key = key
        self.data = {}

        Localization.objects[key] = self

    # Override
    @classmethod
    def saveObjects(cls, free_memory=True):
        localization_path = os.path.join(cls.resource_path, 'localizations')
        for lang, lang_obj in cls.objects.items():
            json_utils.write(os.path.join(localization_path, lang + '.json'), lang_obj.data)

        if free_memory:
            cls.objects = {}

    @classmethod
    def loadObjects(cls):
        localization_path = os.path.join(cls.resource_path, 'localizations')
        os.makedirs(localization_path, exist_ok=True)

        for file in os.listdir(localization_path):
            if file.endswith('.json'):
                file_name = file.split('.')[0]
                cls.objects[file_name] = json_utils.read(
                    os.path.join(localization_path, file_name + '.json')
                )
