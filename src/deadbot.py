import os
import mwclient
import argparse

from utils import pages
from decompiler import decompile

"""
DeadBot pulls all aggregated data for heros, items ,buildings and more to populate
attribute values on the deadlock wiki via the MediaWiki API

A DeadBot user has been created for this purpose, so the password will be needed
to run this locally. However local usage should be limited exclusively to testing
"""


class DeadBot:
    def __init__(self):
        self.edit_counter = 0

        site = mwclient.Site('deadlocked.wiki', path='/')
        site.login('DeadBot', os.environ.get('BOT_WIKI_PASSWORD'))

        self.attribute_pages = [
            page for page in site.pages if pages.page_has_category(page, 'Category:Attribute')
        ]

    def push_lane(self):
        for page in self.attribute_pages:
            self._update_page(page)

    def _update_page(self, page):
        updated_text = 'all the stats'

        # Save the page with the updated content
        if self.edit_counter != 0:
            page.save(updated_text, summary='DeadBot auto-update')
            print(f"Page '{page.name}' updated - {self.edit_counter} new changes")
        else:
            print(f"No changes made to '{page.name}'")


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog='DeadBot',
        description='Bot that lives to serve deadlocked.wiki',
        epilog='Process Deadlock game files and extract data and stats',
    )

    # Setup / Base config Flags
    parser.add_argument(
        '-i',
        '--dl_path',
        help='Path to Deadlock game files (also set with DEADLOCK_PATH environment variable)',
        default=os.getenv('DEADLOCK_PATH'),
    )
    parser.add_argument(
        '-w',
        '--workdir',
        help='Directory for temp working files (also set with WORK_DIR environment variable)',
        default=os.getenv('WORK_DIR', os.path.abspath(os.getcwd()) + '/decompiled-data'),
    )
    parser.add_argument(
        '-o',
        '--output',
        help='Output directory (also set with OUTPUT_DIR environment variable)',
        default=os.getenv('OUTPUT_DIR', os.path.abspath(os.getcwd()) + '/output-data'),
    )
    parser.add_argument(
        '--decompiler_cmd',
        help='Command for Valve Resource Format tool (also set with DECOMPILER_CMD env variable)',
        default=os.getenv('DECOMPILER_CMD', 'tools/Decompiler'),
    )

    # Operational Flags
    parser.add_argument(
        '-d',
        '--decompile',
        action='store_true',
        help='Decompiles Deadlock game files. (also set with DECOMPILE environment variable)',
    )
    parser.add_argument(
        '-b',
        '--bot_push',
        action='store_true',
        help='Push current data to wiki (also set with BOT_PUSH environment variable)',
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    true_args = [
        True,
        'true',
        'True',
        'TRUE',
        't',
        'T',
        1,
    ]

    if args.decompile or os.getenv('DECOMPILE', False) in true_args:
        print('Decompiling source files...')
        decompile.decompile(args.dl_path, args.workdir, args.output, args.decompiler_cmd)
    else:
        print('! Skipping Decompiler !')

    if args.bot_push or os.getenv('BOT_PUSH', False) in true_args:
        print('Running DeadBot...')
        bot = DeadBot()
        bot.push_lane()
    else:
        print('! Skipping DeadBot !')


if __name__ == '__main__':
    main()
