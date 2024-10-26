import os
import argparse

ARG_PARSER = argparse.ArgumentParser(
    prog='DeadBot',
    description='Bot that lives to serve deadlocked.wiki',
    epilog='Process Deadlock game files and extract data and stats',
)


def arg_group_base(parser):
    group_base = parser.add_argument_group('path configs')
    group_base.add_argument(
        '-i',
        '--dl_path',
        help='Path to Deadlock game files (also set with DEADLOCK_PATH environment variable)',
        default=os.getenv('DEADLOCK_PATH'),
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
        '--decompiler_cmd',
        help='Command for Valve Resource Format tool (also set with DECOMPILER_CMD env variable)',
        default=os.getenv('DECOMPILER_CMD', 'tools/Decompiler'),
    )
    group_base.add_argument(
        '--import_files',
        help='Import the decompiled game files from an S3 bucket',
    )
    group_base.add_argument(
        '--build_num',
        help='Build number of the game files to be used. Defaults to current build',
        default=os.getenv('BUILD_NUM', None),
    )
    group_base.add_argument(
        '--steam_username',
        help='Steam username for downloading game files (also set with STEAM_USERNAME environment variable)',
        default=os.getenv('STEAM_USERNAME', None),
    )
    group_base.add_argument(
        '--steam_password',
        help='Steam password for downloading game files (also set with STEAM_PASSWORD environment variable)',
        default=os.getenv('STEAM_PASSWORD', None),
    )
    group_base.add_argument(
        '--depot_downloader_cmd',
        help='Path to DepotDownloader executable (also set with DEPOT_DOWNLOADER_CMD environment variable)',
        default=os.getenv('DEPOT_DOWNLOADER_CMD', None),
    )
    group_base.add_argument(
        '--parse_versions',
        help='Parse version data to link data to manifest id (also set with PARSE_VERSIONS environment variable)',
        default=os.getenv('PARSE_VERSIONS', False),
    )


# Parameters and arguments and flags oh my
def arg_group_s3(parser):
    # s3 config
    group_s3 = parser.add_argument_group('s3 config')
    group_s3.add_argument(
        '--iam_key',
        help='AWS iam key for updating bucket (overrides IAM_KEY environment variable)',
        default=os.getenv('IAM_KEY'),
    )
    group_s3.add_argument(
        '--iam_secret',
        help='AWS iam secret for updating bucket (overrides IAM_SECRET environment variable)',
        default=os.getenv('IAM_SECRET'),
    )
    group_s3.add_argument(
        '--bucket',
        help='S3 bucket name to push to (overrides BUCKET environment variable)',
        default=os.getenv('BUCKET', 'deadlock-game-files'),
    )
    return group_s3


def arg_group_action(parser):
    group_actions = parser.add_argument_group('bot actions')
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
        '-b',
        '--bot_push',
        action='store_true',
        help='Push current data to wiki (also set with BOT_PUSH environment variable)',
    )
    group_actions.add_argument(
        '-s',
        '--s3_push',
        action='store_true',
        help='Push current data to s3',
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
    arg_group_s3(ARG_PARSER)
    # Operational Flags
    arg_group_action(ARG_PARSER)
    args = ARG_PARSER.parse_args()

    # environment var checks for flags
    if not args.decompile:
        args.decompile = os.getenv('DECOMPILE', False)
    if not args.parse:
        args.parse = os.getenv('PARSE', False)
    if not args.changelogs:
        args.changelogs = os.getenv('CHANGELOGS', False)
    if not args.bot_push:
        args.bot_push = os.getenv('BOT_PUSH', False)
    if not args.s3_push:
        args.s3_push = os.getenv('S3_PUSH', False)
    if not args.import_files:
        args.import_files = os.getenv('IMPORT_FILES', False)
    return args
