#!/usr/bin/env python3
import os

from dotenv import load_dotenv

from utils import csv_writer
from decompiler import decompile
import constants
from changelogs import parse_changelogs, fetch_changelogs
from parser import parser
from parser.parsers import versions
from external_data.data_transfer import DataTransfer
from wiki.upload import WikiUpload
from utils.string_utils import is_truthy
from versioning import steamcmd

load_dotenv()


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
        decompile.decompile(args.dl_path, args.workdir, args.decompiler_cmd, args.force)
    else:
        print('! Skipping Decompiler !')

    if is_truthy(True):
        print('Retrieving the most recent manifest-id with SteamCMD...')
        act_versioning(args)
    else:
        print('! Skipping Versioning !')

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

    if is_truthy(args.parse_versions):
        print('Parsing Versions...')
        act_parse_versions(args)
    else:
        print('! Skipping Versions !')

    if is_truthy(args.bot_push):
        print('Running Wiki Upload...')
        wiki_upload = WikiUpload(args.output)
        wiki_upload.update_data_pages()
    else:
        print('! Skipping Wiki Upload !')

    if is_truthy(args.s3_push):
        if args.iam_key and args.iam_secret:
            data_transfer.export_data()
        else:
            print('[ERROR] iam_key and iam_secret must be set for s3')

    print('\nDone!')


def act_parse_versions(args):
    versions.VersionParser(
        args.output, args.depot_downloader_dir, args.steam_username, args.steam_password
    ).run()


def act_gamefile_parse(args):
    game_parser = parser.Parser(args.workdir, args.output)
    game_parser.run()
    print('Exporting to CSV...')
    csv_writer.export_json_file_to_csv('item-data', args.output)
    csv_writer.export_json_file_to_csv('hero-data', args.output)


def act_changelog_parse(args):
    changelog_output = args.output + '/changelogs/'
    os.makedirs(changelog_output, exist_ok=True)
    herolab_patch_notes_path = os.path.join(
        args.workdir, 'localizations', 'patch_notes', 'citadel_patch_notes_english.json'
    )
    chlog_fetcher = fetch_changelogs.ChangelogFetcher(update_existing=False)

    # load localization data
    chlog_fetcher.load_localization(args.output)
    # load existing changelogs
    chlog_fetcher.get_txt(os.path.join(changelog_output, 'raw'))
    # fetch / process rss + forum content
    chlog_fetcher.get_rss(constants.CHANGELOG_RSS_URL)
    # create fetcher and parser
    chlog_fetcher.get_txt(os.path.join(args.inputdir, 'raw-changelogs'))
    # get changelogs from gamefiles (herolabs)
    chlog_fetcher.get_gamefile_changelogs(herolab_patch_notes_path)
    # save combined changelogs to output
    chlog_fetcher.changelogs_to_file(changelog_output, args.inputdir)

    # Now that we gathered the changelogs, extract out data
    chlog_parser = parse_changelogs.ChangelogParser(args.output)
    chlog_parser.run_all(chlog_fetcher.changelogs)
    return chlog_parser


def act_versioning(args):
    manifest_id = steamcmd.SteamCMD(args.steam_cmd, constants.APP_ID).run()
    print(f'Found manifest id: {manifest_id}')


if __name__ == '__main__':
    main()
