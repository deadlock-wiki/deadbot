#!/usr/bin/env python3
import os
import sys
from loguru import logger

from dotenv import load_dotenv

from steam.depot_downloader import DepotDownloader
from utils import csv_writer
from decompiler.decompiler import Decompiler
import constants
from changelogs import parse_changelogs, fetch_changelogs
from parser import parser
from utils.process import run_process
from wiki.upload import WikiUpload
from utils.string_utils import is_truthy

load_dotenv()


def main():
    # load arguments from constants file
    args = constants.ARGS

    # setup custom logger
    logger.remove(0)
    log_level = 'TRACE' if is_truthy(args.verbose) else 'INFO'
    logger.add(
        sys.stderr,
        level=log_level,
        format='<white><dim>{time:YYYY-MM-DD HH:mm:ss.SSS} | </dim>' '</white><level>{level:<7} <dim>|</dim> <normal>{message}</normal></level>',
    )

    # import game files from steamdb github and localization files using depot downloader
    if is_truthy(args.import_files):
        logger.info('Importing game files...')
        script_path = os.path.join(os.path.dirname(__file__), 'steam/steam_db_download_deadlock.sh')
        run_process(script_path, name='download-deadlock-files')
        # non-english localizations are imported using depot downloader
        if not is_truthy(args.english_only):
            logger.info('Downloading non-english localizations...')
            DepotDownloader(
                output_dir=args.workdir,
                deadlock_dir=args.dldir,
                depot_downloader_cmd=args.depot_downloader_cmd,
                steam_username=args.steam_username,
                steam_password=args.steam_password,
                force=args.force,
            ).run(args.manifest_id)
    else:
        logger.trace('! Skipping Import !')

    if is_truthy(args.decompile):
        logger.info('Decompiling source files...')
        Decompiler(deadlock_dir=args.dldir, work_dir=args.workdir, force=args.force).run()
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

    if is_truthy(args.wiki_upload):
        logger.info('Running Wiki Upload...')
        wiki_upload = WikiUpload(args.output)
        wiki_upload.run()
    else:
        logger.trace('! Skipping Wiki Upload !')

    logger.success('Done!')


def act_gamefile_parse(args):
    game_parser = parser.Parser(args.workdir, args.output)
    game_parser.run()
    logger.trace('Exporting to CSV...')
    csv_writer.export_json_file_to_csv('item-data', args.output)
    csv_writer.export_json_file_to_csv('hero-data', args.output)


def act_changelog_parse(args):
    herolab_patch_notes_path = os.path.join(args.workdir, 'localizations', 'patch_notes', 'citadel_patch_notes_english.json')
    chlog_fetcher = fetch_changelogs.ChangelogFetcher(
        update_existing=False,
        input_dir=args.inputdir,
        output_dir=args.output,
        herolab_patch_notes_path=herolab_patch_notes_path,
    )
    chlog_fetcher.run()

    chlog_parser = parse_changelogs.ChangelogParser(args.output)
    chlog_parser.run_all(chlog_fetcher.changelogs)
    chlog_parser.format_and_save_wikitext_changelogs(
        chlog_fetcher.changelogs,
        chlog_fetcher.changelog_configs,
    )
    return chlog_parser


if __name__ == '__main__':
    main()
    