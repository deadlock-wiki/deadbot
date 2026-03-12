#!/usr/bin/env python3
import os
import sys
from loguru import logger

from dotenv import load_dotenv

from steam.depot_downloader import DepotDownloader
from utils import csv_writer, game_utils, meta_utils
from decompiler.decompiler import Decompiler
import constants
from changelogs import parse_changelogs, fetch_changelogs
from parser import parser
from utils.parameters import Args
from utils.process import run_process
from utils.discord_notifier import send_wiki_update_notification, send_error_notification
from wiki.upload import WikiUpload

load_dotenv()


def main():
    # load arguments from constants file
    args = constants.ARGS

    # setup custom logger
    logger.remove(0)
    log_level = 'TRACE' if args.verbose else 'INFO'
    logger.add(
        sys.stderr,
        level=log_level,
        format='<white><dim>{time:YYYY-MM-DD HH:mm:ss.SSS} | </dim>' '</white><level>{level:<7} <dim>|</dim> <normal>{message}</normal></level>',
    )

    # import game files from steamdb github and localization files using depot downloader
    if args.import_files:
        logger.info('Importing game files...')
        script_path = os.path.join(os.path.dirname(__file__), 'steam/steam_db_download_deadlock.sh')
        run_process(script_path, name='download-deadlock-files')
        # non-english localizations are imported using depot downloader
        if not args.english_only:
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
        act_changelog_parse(args)
    else:
        logger.trace('! Skipping Changelogs !')

    if args.wiki_upload:
        logger.info('Running Wiki Upload...')
        try:
            wiki_upload = WikiUpload(args.output, dry_run=args.dry_run)
            upload_summary = wiki_upload.run()
            upload_summary['game_version'] = game_utils.load_game_info(f'{args.output}/version.txt').get('ClientVersion', 'Unknown')
            upload_summary['deadbot_version'] = meta_utils.get_deadbot_version()

            something_changed = upload_summary['data_pages_updated'] or upload_summary['changelogs_uploaded'] or upload_summary['hotfixes_applied']

            if something_changed:
                send_wiki_update_notification(args.discord_webhook, upload_summary, dry_run=args.dry_run)
            else:
                logger.info('No changes detected, skipping Discord notification')
        except Exception as e:
            send_error_notification(args.discord_webhook, e, dry_run=args.dry_run)
            raise
    else:
        logger.trace('! Skipping Wiki Upload !')

    logger.success('Done!')


def act_gamefile_parse(args: Args):
    game_parser = parser.Parser(args.workdir, args.output, english_only=args.english_only)
    game_parser.run()
    logger.trace('Exporting to CSV...')
    csv_writer.export_json_file_to_csv('item-data', args.output)
    csv_writer.export_json_file_to_csv('hero-data', args.output)


def act_changelog_parse(args: Args):
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
