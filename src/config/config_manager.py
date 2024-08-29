# Manages per-user configurations
import json
import os

import subprocess


# Get the root of the Git repository
# Preferably moved to a Utilities file; tried 'from src.utils.pathing import get_repo_path'
# but wasnt able to find src module, need to look into alternatives
def get_repo_path():
    try:
        # Run the git command to find the repository root
        repo_path = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'], text=True
        ).strip()
        return repo_path
    except subprocess.CalledProcessError:
        print('Error: Not inside a Git repository.')
        return None


CONFIG_FILE = os.path.join(get_repo_path(), 'src/config/user_config.json')
# print("CONFIG_FILE: ", CONFIG_FILE)


def load_config():
    """Load the configuration from the JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save the configuration to the JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def set_path(key, path):
    """Set a specific path in the config."""
    config = load_config()
    config[key] = path
    save_config(config)
    print(f"Path for '{key}' set to '{path}'.")


def get_path(key):
    """Get a specific path from the config."""
    config = load_config()
    return config.get(key, '')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Manage user-specific paths.')
    parser.add_argument('--set', nargs=2, metavar=('key', 'path'), help='Set a path.')
    parser.add_argument('--get', metavar='key', help='Get a path.')

    args = parser.parse_args()

    if args.set:
        set_path(args.set[0], args.set[1])
    elif args.get:
        print(get_path(args.get))
