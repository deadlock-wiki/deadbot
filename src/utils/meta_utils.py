import tomllib


def get_deadbot_version():
    # Read the file and parse the version
    with open('pyproject.toml', 'rb') as f:
        pyproject_data = tomllib.load(f)

    deadbot_version = pyproject_data.get('tool', {}).get('poetry', {}).get('version')
    return deadbot_version
