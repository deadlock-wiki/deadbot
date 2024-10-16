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
    deadlock_path = os.getenv('DEADLOCK_PATH', 'default value')
    decompiler_cmd = os.getenv('DECOMPILER_CMD', deadlock_path)

    # Or
    deadlock_path = get_config_value('DEADLOCK_PATH')
    decompiler_cmd = get_config_value('DECOMPILER_CMD')

    print('deadlock_path:', deadlock_path)
    print('decompiler_cmd', decompiler_cmd)
