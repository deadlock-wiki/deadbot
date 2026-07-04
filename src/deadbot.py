#!/usr/bin/env python3
import os
import sys
from loguru import logger

from dotenv import load_dotenv

from steam.depot_downloader import DepotDownloader
from utils import csv_writer
from decompiler.decompiler import Decompiler
from changelogs import parse_changelogs, fetch_changelogs
from parser import parser
from utils.meta_utils import get_deadbot_version
from utils.parameters import load_arguments, Args
from utils.process import run_process
from wiki.upload import WikiUpload
from wiki.changelog_utils import fetch_existing_wiki_updates

load_dotenv()


def main():
    args = load_arguments()

    # setup custom logger
    logger.remove(0)
    log_level = 'TRACE' if args.verbose else 'INFO'
    logger.add(
        sys.stderr,
        level=log_level,
        format='<white><dim>{time:YYYY-MM-DD HH:mm:ss.SSS} | </dim>' '</white><level>{level:<7} <dim>|</dim> <normal>{message}</normal></level>',
    )

    logger.info(f'Running Deadbot v{get_deadbot_version()}')
    # import game files from steamdb github and localization + map files using depot downloader
    if args.import_files:
        logger.info('Importing game files...')
        run_process(['steam/steam_db_download_deadlock.sh', args.dldir], name='download-deadlock-files')

        # non-english localizations are imported using depot downloader
        localization_filelist_path = None
        if not args.english_only:
            logger.info('Downloading non-english localizations...')
            localization_filelist_path = os.path.join(os.path.dirname(__file__), 'steam', 'depot_downloader_file_list.txt')
        else:
            logger.trace('! Skipping non-english localizations download !')

        misc_files = []
        if args.parse_map:
            logger.info('Downloading map...')
            misc_files.extend(['game/citadel/maps/dl_midtown.vpk'])
        else:
            logger.trace('! Skipping map download !')

        if localization_filelist_path is not None or len(misc_files) != 0:
            depot_downloader = DepotDownloader(
                output_dir=args.workdir,
                deadlock_dir=args.dldir,
                steam_username=args.steam_username,
                steam_password=args.steam_password,
            )
            depot_downloader.download_files(
                files=misc_files,
                file_list_path=localization_filelist_path,
                manifest_id=args.manifest_id,
                logger_name='depot-downloader',
            )
    else:
        logger.trace('! Skipping Import !')

    if args.decompile:
        logger.info('Decompiling source files...')
        Decompiler(deadlock_dir=args.dldir, work_dir=args.workdir, force=args.force).run()
    else:
        logger.trace('! Skipping Decompiler !')

    if args.parse:
        logger.info('Parsing decompiled files...')
        act_gamefile_parse(args)
    else:
        logger.trace('! Skipping Parser !')

    if args.changelogs:
        logger.info('Parsing Changelogs...')
        _, pending_ids, wiki_updates = act_changelog_parse(args)
    else:
        pending_ids = None
        wiki_updates = None
        logger.trace('! Skipping Changelogs !')

    if args.wiki_upload:
        logger.info('Running Wiki Upload...')
        wiki_upload = WikiUpload(args.output, dry_run=args.dry_run, pending_changelog_ids=pending_ids, wiki_updates=wiki_updates)
        wiki_upload.run()
    else:
        logger.trace('! Skipping Wiki Upload !')

    logger.success('Done!')


def act_gamefile_parse(args: Args):
    game_parser = parser.Parser(args.workdir, args.output, args.dldir, english_only=args.english_only, parse_map=args.parse_map)
    game_parser.run()
    logger.trace('Exporting to CSV...')
    csv_writer.export_json_file_to_csv('item-data', args.output)
    csv_writer.export_json_file_to_csv('hero-data', args.output)


def act_changelog_parse(args: Args):
    # Single wiki query at the start — fetches both the date set (for pending
    # computation) and the full (date, title) tuple list (for upload linking).
    # Both ChangelogFetcher and WikiUpload receive these, avoiding redundant scans.
    existing_dates, wiki_updates = fetch_existing_wiki_updates()

    chlog_fetcher = fetch_changelogs.ChangelogFetcher(
        update_existing=False,
        input_dir=args.inputdir,
        output_dir=args.output,
        existing_dates=existing_dates,
    )
    chlog_fetcher.run()

    pending_ids = chlog_fetcher.get_pending_changelog_ids()

    chlog_parser = parse_changelogs.ChangelogParser(args.output)
    chlog_parser.run_all(chlog_fetcher.changelogs, pending_ids=pending_ids)
    chlog_parser.format_and_save_wikitext_changelogs(
        chlog_fetcher.changelogs,
        chlog_fetcher.changelog_configs,
        pending_ids=pending_ids,
    )
    return chlog_parser, pending_ids, wiki_updates


if __name__ == '__main__':
    main()
