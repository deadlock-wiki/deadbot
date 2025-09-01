import os
import argparse
from dotenv import load_dotenv

load_dotenv()

ARG_PARSER = argparse.ArgumentParser(
    prog='DeadBot',
    description='Bot that lives to serve deadlock.wiki',
    epilog='Process Deadlock game files and extract data and stats',
)

"""
When adding parameters:
- Add to the proper group
- Ensure the help message follows previous standards
- If the parameter is a boolean, use `action='store_true'`, 
    This allows it to be called like `--verbose` instead of `--verbose True`
"""


def arg_group_base(parser):
    group_base = parser.add_argument_group('path configs')
    group_base.add_argument(
        '--dldir',
        help='Path to Deadlock game files (also set with DEADLOCK_DIR environment variable)',
        default=os.getenv('DEADLOCK_DIR'),
    )
    group_base.add_argument(
        '-w',
        '--workdir',
        help='Directory for temp working files (also set with WORK_DIR environment variable)',
        default=os.getenv('WORK_DIR', os.path.abspath(os.getcwd()) + '/decompiled-data'),
    )
    group_base.add_argument(
        '-n',
        '--inputdir',
        help='Input directory for changelogs and wiki pages (also set with OUTPUT_DIR env variable)',
        default=os.getenv('INPUT_DIR', os.path.abspath(os.getcwd()) + '/input-data'),
    )
    group_base.add_argument(
        '-o',
        '--output',
        help='Output directory (also set with OUTPUT_DIR environment variable)',
        default=os.getenv('OUTPUT_DIR', os.path.abspath(os.getcwd()) + '/output-data'),
    )
    group_base.add_argument(
        '--english-only',
        action='store_true',
        help='Only parse for english localizations (also set with ENGLISH_ONLY environment variable)',
        default=os.getenv('ENGLISH_ONLY', False),
    )
    group_base.add_argument(
        '--force',
        action='store_true',
        help='Forces decompilation even if game files and workdir versions match',
        default=os.getenv('FORCE', False),
    )
    group_base.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Print verbose output for extensive logging',
        default=os.getenv('VERBOSE', False),
    )


def arg_group_steam(parser):
    group_steam = parser.add_argument_group('steam config')
    group_steam.add_argument(
        '--steam_username',
        help='Steam username for downloading game files (also set with STEAM_USERNAME ' + 'environment variable)',
        default=os.getenv('STEAM_USERNAME', None),
    )
    group_steam.add_argument(
        '--steam_password',
        help='Steam password for downloading game files (also set with STEAM_PASSWORD environment' + ' variable)',
        default=os.getenv('STEAM_PASSWORD', None),
    )
    group_steam.add_argument(
        '--depot_downloader_cmd',
        help='Path to DepotDownloader directory that contains the executable (also set with DEPOT_DOWNLOADER_CMD environment' + ' variable)',
        default=os.getenv('DEPOT_DOWNLOADER_CMD', None),
    )
    group_steam.add_argument(
        '--manifest_id',
        help="Manifest id to download, defaults to 'latest' (also set with MANIFEST_ID environment variable). Browse them at https://steamdb.info/depot/1422456/manifests/",
        default=os.getenv('MANIFEST_ID', None),
    )
    return group_steam


def arg_group_action(parser):
    group_actions = parser.add_argument_group('bot actions')
    group_actions.add_argument(
        '-i',
        '--import_files',
        help='Import the game files from SteamDB and localization files using DepotDownloader (also set with IMPORT_FILES environment variable)',
    )
    group_actions.add_argument(
        '-d',
        '--decompile',
        action='store_true',
        help='Decompiles Deadlock game files. (also set with DECOMPILE environment variable)',
    )
    group_actions.add_argument(
        '-p',
        '--parse',
        action='store_true',
        help='Parses decompiled game files into json and csv (overrides PARSE env variable)',
    )
    group_actions.add_argument(
        '-u',
        '--wiki_upload',
        action='store_true',
        help='Upload parsed data to the Wiki (also set with WIKI_UPLOAD environment variable)',
    )
    group_actions.add_argument(
        '-c',
        '--changelogs',
        action='store_true',
        help='Fetch/parse forum and local changelogs. (also set with CHANGELOGS env variable)',
    )
    return group_actions


def load_arguments():
    # Setup / Base config Flags
    arg_group_base(ARG_PARSER)
    arg_group_steam(ARG_PARSER)
    # Operational Flags
    arg_group_action(ARG_PARSER)
    args = ARG_PARSER.parse_args()

    # environment var checks for flags
    if not args.import_files:
        args.import_files = os.getenv('IMPORT_FILES', False)
    if not args.decompile:
        args.decompile = os.getenv('DECOMPILE', False)
    if not args.parse:
        args.parse = os.getenv('PARSE', False)
    if not args.changelogs:
        args.changelogs = os.getenv('CHANGELOGS', False)
    if not args.wiki_upload:
        args.wiki_upload = os.getenv('WIKI_UPLOAD', False)
    if not args.verbose:
        args.verbose = os.getenv('VERBOSE', False)
    return args
