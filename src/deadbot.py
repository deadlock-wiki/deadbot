#!/usr/bin/env python3
import os
import mwclient

from utils import pages, csv_writer
from decompiler import decompile
import constants
from changelogs import parse_changelogs, fetch_changelogs
from parser import parser
from external_data.data_transfer import DataTransfer
from utils.string_utils import is_truthy


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
    changelog_output = args.output + '/changelogs/raw'
    os.makedirs(changelog_output, exist_ok=True)
    chlog_fetcher = fetch_changelogs.ChangelogFetcher()
    # load existing changelogs
    chlog_fetcher.get_txt(changelog_output)
    # fetch / process rss + forum content
    chlog_fetcher.get_rss(constants.CHANGELOG_RSS_URL, update_existing=False)
    # create fetcher and parser
    chlog_fetcher.get_txt(args.inputdir + '/raw-changelogs')
    # save combined changelogs to output
    chlog_fetcher.changelogs_to_file(changelog_output)

    # Now that we gathered the changelogs, extract out data
    chlog_parser = parse_changelogs.ChangelogParser(args.output)
    chlog_parser.run_all(chlog_fetcher.changelogs_by_date)
    return chlog_parser


def main():
    # load arguments from constants file
    args = constants.ARGS

    data_transfer = DataTransfer(args.workdir, args.bucket, args.iam_key, args.iam_secret)

    if is_truthy(args.import_files):
        if is_truthy(args.decompile):
            print('[WARN] Skipping import as it will be overwritten by Decompile step')
        elif args.iam_key and args.iam_secret:
            data_transfer.import_data(version=args.build_num)
        else:
            print('[ERROR] iam_key and iam_secret must be set for s3')

    if is_truthy(args.decompile):
        print('Decompiling source files...')
        decompile.decompile(args.dl_path, args.workdir, args.output, args.decompiler_cmd)
    else:
        print('! Skipping Decompiler !')

    if is_truthy(args.parse):
        print('Parsing decompiled files...')
        act_gamefile_parse(args)
    else:
        print('! Skipping Parser !')

    if is_truthy(args.changelogs):
        print('Parsing Changelogs...')
        act_changelog_parse(args)
    else:
        print('! Skipping Changelogs !')

    if is_truthy(args.bot_push):
        print('Running DeadBot...')
        bot = DeadBot()
        bot.push_lane()
    else:
        print('! Skipping DeadBot !')

    if is_truthy(args.s3_push):
        if args.iam_key and args.iam_secret:
            data_transfer.export_data()
        else:
            print('[ERROR] iam_key and iam_secret must be set for s3')

    print('\nDone!')


if __name__ == '__main__':
    main()
