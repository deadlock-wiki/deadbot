import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from utils.config_manager import get_config_value
import utils.json_utils as json_utils
import json


class Resource:
    output_path = get_config_value('OUTPUT_DIR')
    resource_path = os.path.join(output_path, 'resources')

    
    @classmethod
    def save_objects(cls, move_data_attr_up_layer=False, free_memory=True):
        """
        Save all object's of a given class from memory to json file
        :param move_data_attr_up_layer: If False, doesn't move the data attribute up a layer in the json file
        :param free_memory: If True, clears the objects hash after saving
        """

        """
        move_data_attr_up_layer = False (default)
        {
            obj_key: {
                Key: obj_key,
                attr1: value,
                attr2: value,
                ...
                Data: {
                    unassigned_attr1: value
                }
            },
        }

        move_data_attr_up_layer = True
        {
            obj_key: {
                Key: obj_key,
                attr1: value,
                attr2: value,
                ...
                unassigned_attr1: value
            },
        }
        """
        class_name_str = cls.__name__

        os.makedirs(Resource.resource_path, exist_ok=True)
        path = os.path.join(Resource.resource_path, class_name_str + '.json')

        # Convert hash of objects to hash of hashes
        hash = {}
        for obj_key, obj in cls.objects.items():
            if move_data_attr_up_layer:
                hash[obj_key] = obj.__dict__
                hash[obj_key].update(obj.Data)
                hash[obj_key].pop('Data', None)
            else:
                hash[obj_key] = obj.__dict__
            # Remove 'Key' attribute
            hash[obj_key].pop('Key', None)

        # Write to file
        json_utils.write(path, hash)

        if free_memory:
            cls.objects = {}

    # Load all object's of a given class from json file to memory
    @classmethod
    def load_objects(cls):
        """
        Load all object's of a given class from json file to memory
        """
        class_name_str = cls.__name__

        os.makedirs(Resource.resource_path, exist_ok=True)
        path = os.path.join(Resource.resource_path, class_name_str + '.json')

        # Convert hash of hashes to hash of objects
        with open(path) as json_file:
            data = json.load(json_file)
            for obj_key, obj_data in data.items():
                obj = cls(obj_key)
                for attr in obj_data:
                    if attr in obj.__dict__:
                        setattr(obj, attr, obj_data[attr])
                    else:
                        obj.Data[attr] = obj_data[attr]

    # Store all object's of a given class from a hash to memory, 
    # where 1st level is the object key, and 2nd level is its attributes
    @classmethod
    def store_resources(cls, hash):
        for obj_key, obj_data in hash.items():
            obj = cls(obj_key)
            for key, value in obj_data.items():
                # If the key is an attribute the object has, store it in the attribute
                if key in obj.__dict__:
                    setattr(obj, key, value)
                else:
                    # Otherwise put it in the data attribute
                    obj.Data[key] = value

    # Placeholder for use in ChangelogsParser
    # After changelog rework, this will be removed
    @classmethod
    def objs_to_hash(cls):
        hash = {}
        # Iterate objects
        for obj_key, obj in cls.objects.items():
            hash[obj_key] = obj.__dict__
        return hash

    def get_prop(self, prop):
        return self.get(prop, None)
