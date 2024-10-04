import os
import mwclient
import argparse
from utils import pages, csv_writer
from decompiler import decompile
from parser import parser

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
                    epilog='Process Deadlock game files and extract data and stats')


    # Setup / Base config Flags
    parser.add_argument(
        "-i", "--dl_path", 
        help="Path to Deadlock game files (overrides DEADLOCK_PATH environment variable)", 
        default=os.getenv('DEADLOCK_PATH'))
    parser.add_argument(
        "-w", "--workdir", 
        help="Directory for temp working files (overrides WORK_DIR environment variable)",
        default=os.getenv('WORK_DIR',os.path.abspath(os.getcwd())+'/decompiled-data'))
    parser.add_argument(
        "-o", "--output", 
        help="Output directory (overrides OUTPUT_DIR environment variable)", 
        default=os.getenv('OUTPUT_DIR',os.path.abspath(os.getcwd())+'/output-data'))
    parser.add_argument(
        "-", "--decompiler_cmd", 
        help="Command for Valve Resource Format tool (overrides DECOMPILER_CMD env variable)",
        default=os.getenv('DECOMPILER_CMD','Decompiler'))    

    # Operational Flags
    parser.add_argument(
        "-d", "--decompile", 
        help="Decompiles Deadlock game files (overrides DECOMPILE environment variable)", 
        default=os.getenv('DECOMPILE',False))
    parser.add_argument(
        "-p", "--parse", 
        help="Parses decompiled game files into json and csv (overrides PARSE env variable)", 
        default=os.getenv('PARSE',False))
    parser.add_argument(
        "-b", "--bot_push", 
        help="Push current data to wiki (overrides BOT_PUSH environment variable)", 
        default=os.getenv('BOT_PUSH',False))
    parser.add_argument(
        "--iam_key",
        help="AWS iam key for updating bucket (overrides IAM_KEY environment variable)", 
        default=os.getenv('IAM_KEY'))
    parser.add_argument(
        "--iam_secret",
        help="AWS iam secret for updating bucket (overrides IAM_SECRET environment variable)", 
        default=os.getenv('IAM_SECRET'))
    parser.add_argument(
        "--bucket",
        help="S3 bucket name to push to (overrides BUCKET environment variable)", 
        default=os.getenv('BUCKET','deadlock-game-files'))

    return parser.parse_args()

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

    if args.parse or os.getenv('PARSE', False) in true_args:
        print("Parsing decompiled files...")
        game_parser = parser.Parser(args.workdir,args.output)
        game_parser.run()
        print("Exporting to CSV...")
        csv_writer.export_json_file_to_csv('item-data', args.output)
        csv_writer.export_json_file_to_csv('hero-data', args.output)
    else:
        print("! Skipping Parser !")

    if args.bot_push or os.getenv('BOT_PUSH', False) in true_args:
        print('Running DeadBot...')
        bot = DeadBot()
        bot.push_lane()
    else:
        print('! Skipping DeadBot !')

    if args.iam_key and args.iam_secret:
        parser.S3(
            args.output,
            args.bucket,
            args.iam_key,
            args.iam_secret
        ).write()

    print("\nDone!")

if __name__ == '__main__':
    main()
