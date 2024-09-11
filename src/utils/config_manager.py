# Manages per-user configurations
import os

from dotenv import load_dotenv

load_dotenv()


# Retrieve a configuration key's associated value from .env
def get_config_value(key):
    # Return the path to the config file

    value = os.getenv(key)
    if value is None:
        raise ValueError(f'Key {key} not found in .env')
    return value


if __name__ == '__main__':
    # Example usages
    deadlock_path = os.getenv('DEADLOCK_PATH')
    decompiler_path = os.getenv('DECOMPILER_PATH')

    # Or
    deadlock_path = get_config_value('DEADLOCK_PATH')
    decompiler_path = get_config_value('DECOMPILER_PATH')

    print('deadlock_path:', deadlock_path)
    print('decompiler_path', decompiler_path)
