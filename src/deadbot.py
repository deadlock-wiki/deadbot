#!/usr/bin/env python3
import os
import mwclient

from utils import pages, csv_writer
from decompiler import decompile
import constants
from changelogs import parse_changelogs, fetch_changelogs
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




def act_gamefile_parse(args):
    game_parser = parser.Parser(args.workdir, args.output)
    game_parser.run()
    print('Exporting to CSV...')
    csv_writer.export_json_file_to_csv('item-data', args.output)
    csv_writer.export_json_file_to_csv('hero-data', args.output)

def act_changelog_parse(args):
    ch_fetcher = fetch_changelogs.ChangelogFetcher()
    # setup the rss url
    if not args.skip_rss:
        ch_fetcher.get_rss(constants.CHANGELOG_RSS_URL)
    # create fetcher and parser
    ch_fetcher.get_txt(args.inputdir + '/raw-changelogs')
    # save combined changelogs to output
    ch_fetcher.changelogs_to_file(args.output + '/changelogs/raw')

    # Now that we gathered the changelogs, extract out data
    ch_parser = parse_changelogs.ChangelogParser(args.output)
    ch_parser.run_all(ch_fetcher.changelogs_by_date)
    return ch_parser

def main():
    args = constants.ARGS

    if args.decompile or os.getenv('DECOMPILE', False) in constants.TRUE_THO:
        print('Decompiling source files...')
        decompile.decompile(args.dl_path, args.workdir, args.output, args.decompiler_cmd)
    else:
        print('! Skipping Decompiler !')

    if args.parse or os.getenv('PARSE', False) in constants.TRUE_THO:
        print('Parsing decompiled files...')
        act_gamefile_parse(args)
    else:
        print('! Skipping Parser !')

    if args.changelogs or (os.getenv('CHLOGS', False) in constants.TRUE_THO):
        print('Parsing Changelogs...')
        act_changelog_parse(args)
    else:
        print('! Skipping Changelogs !')

    if args.bot_push or os.getenv('BOT_PUSH', False) in constants.TRUE_THO:
        print('Running DeadBot...')
        bot = DeadBot()
        bot.push_lane()
    else:
        print('! Skipping DeadBot !')

    if args.s3_push or os.getenv('S3_PUSH', False) in constants.TRUE_THO:
        if args.iam_key and args.iam_secret:
            parser.S3(args.output, args.bucket, args.iam_key, args.iam_secret).write()
        else:
            print('Error: iam_key and iam_secret must be set for s3')

    print('\nDone!')


if __name__ == '__main__':
    main()
