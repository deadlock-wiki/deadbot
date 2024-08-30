# Manages per-user configurations
import os

from dotenv import load_dotenv

env_path = '.env.local'

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    raise FileNotFoundError(f'File {env_path} not found')


# Retrieve a configuration key's associated value from .env.local
def get_config_value(key):
    # Return the path to the config file

    value = os.getenv(key)
    if value is None:
        raise ValueError(f'Key {key} not found in .env.local')
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
