import sys
import tomllib
from typing import TypedDict, Optional, Literal
from pathlib import Path

VERSION_DIR = Path('pyproject.toml')
VERSION_FILE = Path('src/_version.py')


class VersionInfo(TypedDict):
    major: int
    minor: int
    patch: int
    beta: Optional[int]


IncrementType = Literal['major', 'minor', 'patch', 'beta']


def increment_version(increment_type: IncrementType):
    """Increments Deadbot version number

    Args:
        increment_type: The type of increment being used - major, minor, patch, or beta
    """
    version = read_version()

    match increment_type:
        case 'major':
            version['major'] += 1
            version['minor'] = 0
            version['patch'] = 0
            version['beta'] = 0

        case 'minor':
            version['minor'] += 1
            version['patch'] = 0
            version['beta'] = 0

        case 'patch':
            version['patch'] += 1
            version['beta'] = 0

        case 'beta':
            version['beta'] += 1

    write_version(version)
    return


def read_version() -> VersionInfo:
    with open(VERSION_DIR, 'rb') as f:
        pyproject_data = tomllib.load(f)

    version = pyproject_data['tool']['poetry']['version']
    version_components = version.split('-')
    [major, minor, patch] = version_components[0].split('.')

    # no beta is more simply represented as "0" as beta starts at "1"
    beta = 0
    if len(version_components) == 2:
        beta = version_components[1].split('.')[1]

    return {
        'major': int(major),
        'minor': int(minor),
        'patch': int(patch),
        'beta': int(beta),
    }


def write_version(version: VersionInfo):
    version_string = f'{version["major"]}.' f'{version["minor"]}.' f'{version["patch"]}'

    if version['beta']:
        version_string += f'-beta.{version["beta"]}'

    # Update pyproject.toml
    lines = []
    with open(VERSION_DIR, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip().startswith('version ='):
                lines.append(f'version = "{version_string}"\n')
            else:
                lines.append(line)

    with open(VERSION_DIR, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    VERSION_FILE.write_text(
        f"__version__ = '{version_string}'\n",
        encoding='utf-8',
    )


if __name__ == '__main__':
    increment_type = sys.argv[1]
    valid_types = ['major', 'minor', 'patch', 'beta']

    if increment_type not in valid_types:
        raise Exception(f'Invalid increment type "{increment_type}" - must be one of {valid_types}')

    increment_version(increment_type)
