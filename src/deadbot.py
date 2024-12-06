#!/usr/bin/env python3
import os
import sys
import mwclient
from loguru import logger

from dotenv import load_dotenv

from utils import csv_writer
from decompiler import decompile
import constants
from changelogs import parse_changelogs, fetch_changelogs
from parser import parser
from external_data.data_transfer import DataTransfer
from wiki.upload import WikiUpload
from utils.string_utils import is_truthy

load_dotenv()


def main():
    # load arguments from constants file
    args = constants.ARGS

    # setup custom logger
    logger.remove(0)
    log_level = 'TRACE' if is_truthy(args.verbose) else 'INFO'
    logger.add(sys.stderr, level=log_level)

    data_transfer = DataTransfer(args.workdir, args.bucket, args.iam_key, args.iam_secret)

    if is_truthy(args.import_files):
        if is_truthy(args.decompile):
            logger.info('Skipping import as it will be overwritten by Decompile step')
        elif args.iam_key and args.iam_secret:
            data_transfer.import_data(version=args.build_num)
        else:
            raise Exception('iam_key and iam_secret must be set for s3')

    if is_truthy(args.decompile):
        logger.info('Decompiling source files...')
        decompile.decompile(args.dl_path, args.workdir, args.decompiler_cmd, args.force)
    else:
        logger.trace('! Skipping Decompiler !')

    if is_truthy(args.parse):
        logger.info('Parsing decompiled files...')
        act_gamefile_parse(args)
    else:
        logger.trace('! Skipping Parser !')

    if is_truthy(args.changelogs):
        logger.info('Parsing Changelogs...')
        act_changelog_parse(args)
    else:
        logger.trace('! Skipping Changelogs !')

    if is_truthy(args.bot_push):
        logger.info('Running Wiki Upload...')
        wiki_upload = WikiUpload(args.output)
        wiki_upload.update_data_pages()
    else:
        logger.trace('! Skipping DeadBot !')

    if is_truthy(args.s3_push):
        if args.iam_key and args.iam_secret:
            data_transfer.export_data()
        else:
            logger.error('[ERROR] iam_key and iam_secret must be set for s3')

    logger.success('Done!')


def act_gamefile_parse(args):
    game_parser = parser.Parser(args.workdir, args.output)
    game_parser.run()
    logger.trace('Exporting to CSV...')
    csv_writer.export_json_file_to_csv('item-data', args.output)
    csv_writer.export_json_file_to_csv('hero-data', args.output)


def act_changelog_parse(args):
    herolab_patch_notes_path = os.path.join(
        args.workdir, 'localizations', 'patch_notes', 'citadel_patch_notes_english.json'
    )
    chlog_fetcher = fetch_changelogs.ChangelogFetcher(
        update_existing=False,
        input_dir=args.inputdir,
        output_dir=args.output,
        herolab_patch_notes_path=herolab_patch_notes_path,
    )
    chlog_fetcher.run()

    # Now that we gathered the changelogs, extract out data
    chlog_parser = parse_changelogs.ChangelogParser(args.output)
    chlog_parser.run_all(chlog_fetcher.changelogs)
    return chlog_parser


if __name__ == '__main__':
    main()
