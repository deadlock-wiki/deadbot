import argparse
import tomllib
from pathlib import Path
from typing import Literal, TypedDict

VERSION_DIR = Path('pyproject.toml')
VERSION_FILE = Path('src/_version.py')


class VersionInfo(TypedDict):
    major: int
    minor: int
    patch: int
    beta: int | None


IncrementType = Literal['major', 'minor', 'patch', 'beta']


def parse_version_string(version_str: str) -> VersionInfo:
    version_components = version_str.split('-')
    [major, minor, patch] = version_components[0].split('.')

    # no beta is more simply represented as "0" as beta starts at "1"
    beta = 0
    if len(version_components) == 2:
        beta = int(version_components[1].split('.')[1])

    return {
        'major': int(major),
        'minor': int(minor),
        'patch': int(patch),
        'beta': int(beta),
    }


def read_version() -> VersionInfo:
    with open(VERSION_DIR, 'rb') as f:
        pyproject_data = tomllib.load(f)
    version = pyproject_data['tool']['poetry']['version']
    return parse_version_string(version)


def get_next_version(current: VersionInfo, increment_type: IncrementType) -> VersionInfo:
    """Pure function that calculates the next version without side-effects."""
    next_version = current.copy()

    match increment_type:
        case 'major':
            next_version['major'] += 1
            next_version['minor'] = 0
            next_version['patch'] = 0
            next_version['beta'] = 0
        case 'minor':
            next_version['minor'] += 1
            next_version['patch'] = 0
            next_version['beta'] = 0
        case 'patch':
            next_version['patch'] += 1
            next_version['beta'] = 0
        case 'beta':
            next_version['beta'] += 1

    return next_version


def format_version(version: VersionInfo) -> str:
    version_string = f'{version["major"]}.{version["minor"]}.{version["patch"]}'
    if version['beta']:
        version_string += f'-beta.{version["beta"]}'
    return version_string


def write_version(version: VersionInfo):
    version_string = format_version(version)

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


def increment_version(increment_type: IncrementType):
    version = read_version()
    next_version = get_next_version(version, increment_type)
    write_version(next_version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Increment Deadbot version')
    parser.add_argument('increment_type', choices=['major', 'minor', 'patch', 'beta'])
    parser.add_argument('--print-only', action='store_true', help='Print the next version number without writing to files')
    parser.add_argument('--base', type=str, help='Base version string to increment (defaults to reading pyproject.toml)')

    args = parser.parse_args()

    if args.base:
        current_version = parse_version_string(args.base)
    else:
        current_version = read_version()

    next_version = get_next_version(current_version, args.increment_type)

    if args.print_only:
        print(format_version(next_version))
    else:
        write_version(next_version)
