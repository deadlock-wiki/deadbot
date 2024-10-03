import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from utils.config_manager import get_config_value
from utils.json_utils import write
import json

class Resource:
    resource_path = os.path.join(get_config_value('OUTPUT_DIR'), 'resources')

    # Save all object's of a given class from memory to json file
    @classmethod
    def saveObjects(cls):
        class_name_str = cls.__name__
        
        os.makedirs(Resource.resource_path, exist_ok=True)
        path = os.path.join(Resource.resource_path, class_name_str+'.json')

        # Convert hash of objects to hash of hashes
        hash = {}
        for obj_key, obj in cls.objects.items():
            for attr in obj.__dict__:
                if attr == 'Key':
                    continue
                if obj_key not in hash:
                    hash[obj_key] = {}
                hash[obj_key][attr] = getattr(obj, attr)
        
        # Write to file
        write(path, hash)

    # Load all object's of a given class from json file to memory
    @classmethod
    def loadObjects(cls):
        class_name_str = cls.__name__

        os.makedirs(Resource.resource_path, exist_ok=True)
        path = os.path.join(Resource.resource_path, class_name_str+'.json')
        
        # Convert hash of hashes to hash of objects
        with open(path) as json_file:
            data = json.load(json_file)
            for obj_key, obj_data in data.items():
                cls.objects[obj_key] = cls(obj_key)
                # Add data as attributes
                for item in obj_data:
                    setattr(cls.objects[obj_key], item, obj_data[item])

    @classmethod
    def hashToObjs(cls, hash):
        for key, value in hash.items():
            cls.objects[key] = cls(key)
            cls.objects[key].hashToAttrs(value)

    def hashToAttrs(self, data):
        for key, value in data.items():
            setattr(self, key, value)

    def getProperty(self, prop):
        return getattr(self, prop)