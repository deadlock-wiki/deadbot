import os
import mwclient
import json
import re
from datetime import datetime
from typing import List, Tuple, Optional, Set
from utils import json_utils, game_utils, meta_utils
from .pages import DATA_PAGE_FILE_MAP, IGNORE_PAGES
from loguru import logger
from . import changelog_utils


class WikiUpload:
    """
    Uploads a set of specified data to deadlock.wiki via the MediaWiki API
    """

    def __init__(
        self,
        output_dir,
        dry_run=False,
        pending_changelog_ids: Optional[Set[str]] = None,
        wiki_updates: Optional[List[Tuple[datetime, str]]] = None,
    ):
        self.OUTPUT_DIR = output_dir
        self.DATA_NAMESPACE = 'Data'
        # Set of changelog_ids that need processing this run; if None, process all.
        self.pending_changelog_ids = pending_changelog_ids

        if dry_run:
            logger.info('Wiki upload is running in dry-run mode. No changes will be made to the wiki.')
        self.dry_run = dry_run

        game_version = game_utils.load_game_info(f'{self.OUTPUT_DIR}/version.txt')['ClientVersion']
        deadbot_version = meta_utils.get_deadbot_version()
        self.upload_message = f'Deadbot v{deadbot_version}-{game_version}'

        self.site = mwclient.Site('deadlock.wiki', path='/', clients_useragent=f'Deadbot/{deadbot_version}')

        if not self.dry_run:
            self.auth = {
                'user': os.environ.get('BOT_WIKI_USER'),
                'password': os.environ.get('BOT_WIKI_PASS'),
            }

            if not self.auth['user']:
                raise Exception('BOT_WIKI_USER env var is required to upload to wiki')

            if not self.auth['password']:
                raise Exception('BOT_WIKI_PASS env var is required to upload to wiki')

            self.site.login(self.auth['user'], self.auth['password'])

        # Store wiki state; use pre-fetched from caller if provided to avoid
        # a redundant allpages scan (deadbot.py queries once and distributes).
        self.wiki_updates: List[Tuple[datetime, str]] = wiki_updates or []

    def run(self):
        logger.info(f'Uploading Data to Wiki - {self.upload_message}')
        self._update_data_pages()
        if not self.wiki_updates:
            self.wiki_updates = self._get_existing_update_pages()
        self._upload_changelog_pages()
        self._process_hotfixes()
        self._update_latest_chain()

    def _get_existing_update_pages(self) -> List[Tuple[datetime, str]]:
        """
        Fetch all Update pages from wiki and return list of (date, title) tuples.
        Uses the shared single-scan helper in changelog_utils.
        """
        _, wiki_updates = changelog_utils.fetch_existing_wiki_updates(self.site)
        logger.debug(f'Found {len(wiki_updates)} valid update pages in Update namespace')
        return wiki_updates

    def _upload_changelog_pages(self):
        """
        Reads formatted changelog files and uploads them to the wiki.
        Queries wiki state to ensure correct prev_update linking on first upload.
        Only processes changelog_ids in self.pending_changelog_ids (if set).
        """
        changelog_dir = os.path.join(self.OUTPUT_DIR, 'changelogs', 'wiki')
        if not os.path.isdir(changelog_dir):
            logger.trace(f'Changelog wiki directory not found at "{changelog_dir}", skipping changelog upload.')
            return

        logger.info('Uploading changelog pages...')

        # Load changelog configs to check for edit flags
        changelog_configs_path = os.path.join(self.OUTPUT_DIR, 'changelogs', 'changelog_configs.json')
        changelog_configs = json_utils.read(changelog_configs_path, ignore_error=True) or {}

        # Determine which changelog_ids to process this run.
        # Only process pending ids when the set is provided; otherwise fall back
        # to scanning the directory (backward compat).
        if self.pending_changelog_ids is not None:
            # Sort chronologically by date+variant so intra-run prev_update linking works.
            candidate_ids = [
                f.replace('.txt', '') for f in changelog_utils.sort_changelog_files([f'{cid}.txt' for cid in self.pending_changelog_ids])
            ]
        else:
            candidate_ids = [
                f.replace('.txt', '') for f in changelog_utils.sort_changelog_files([f for f in os.listdir(changelog_dir) if f.endswith('.txt')])
            ]

        if not candidate_ids:
            return

        # Track uploads in this run for correct intra-run linking
        uploads_this_run: List[Tuple[datetime, str]] = []

        for changelog_id in candidate_ids:
            filename = f'{changelog_id}.txt'

            # Skip if the post was edited by devs to protect manual wiki edits
            if changelog_configs.get(changelog_id, {}).get('was_edited'):
                logger.info(f'Skipping wiki upload for {changelog_id} because devs edited the post. Manual review required.')
                continue
            try:
                date_obj = changelog_utils.parse_changelog_date_from_id(changelog_id)
                if not date_obj:
                    raise ValueError(f'Invalid date format in {changelog_id}')

                wiki_date_str = f"{date_obj.strftime('%B')}_{date_obj.day},_{date_obj.year}"
                page_title = f'Update:{wiki_date_str}'

                filepath = os.path.join(changelog_dir, filename)
                if not os.path.exists(filepath):
                    logger.trace(f'Wikitext file not found for pending changelog {changelog_id}, skipping.')
                    continue
                with open(filepath, 'r', encoding='utf-8') as f:
                    raw_content = f.read()

                # Calculate correct prev_update based on wiki state + earlier uploads this run
                prev_update_link = changelog_utils.calculate_prev_update_link(date_obj, page_title, self.wiki_updates, uploads_this_run)

                # Inject the link into the wikitext content
                content = changelog_utils.inject_prev_update(raw_content, prev_update_link)

                self.upload_new_page(page_title, content)

                # Track for subsequent iterations in this same run
                uploads_this_run.append((date_obj, page_title))

            except ValueError as e:
                logger.error(f"Could not parse date from changelog filename '{filename}': {e}")
            except Exception as e:
                logger.error(f"Failed to upload changelog from '{filename}': {e}")

    def _process_hotfixes(self):
        """
        Reads specifically identified hotfix sections from the fetcher and appends them
        to their respective existing wiki pages.
        """
        hotfixes_path = os.path.join(self.OUTPUT_DIR, 'changelogs/hotfixes.json')
        hotfixes = json_utils.read(hotfixes_path, ignore_error=True)
        if not hotfixes:
            logger.info('No hotfixes detected to append')
            return

        logger.info(f'Processing {len(hotfixes)} hotfixes for appending...')
        for hotfix in hotfixes:
            try:
                date_obj = datetime.strptime(hotfix['date'], '%Y-%m-%d')
                # Assuming standard naming: Update:Month_Day,_Year
                page_title = f"Update:{date_obj.strftime('%B')}_{date_obj.day},_{date_obj.year}"
                page = self.site.pages[page_title]

                if not page.exists:
                    logger.warning(f'Cannot append hotfix to {page_title} - page does not exist')
                    continue

                current_text = page.text()
                # Idempotency check: don't append if the text is already there
                if hotfix['text'] in current_text:
                    logger.info(f'Hotfix for {page_title} already exists on wiki, skipping.')
                    continue

                # Perform the append before the closing }} of the layout template
                if current_text.strip().endswith('}}'):
                    base_text = current_text.strip()
                    new_page_text = base_text[:-2] + f"\n\n{hotfix['text']}\n}}"

                    logger.info(f'Appending new hotfix section to Wiki page: {page_title}')
                    if not self.dry_run:
                        page.save(new_page_text, summary=f'{self.upload_message}: Appended new hotfix notes')
                        logger.success(f'Successfully appended hotfix to {page_title}')
                else:
                    logger.warning(f"Page {page_title} does not end with '}}', cannot safely append hotfix.")
            except Exception as e:
                logger.error(f"Failed to process hotfix for {hotfix.get('date')}: {e}")

    def _update_data_pages(self):
        namespace_id = self._get_namespace_id(self.DATA_NAMESPACE)
        for page in self.site.allpages(namespace=namespace_id):
            page_name_obj = self._split_page_name(page.name)
            namespace = page_name_obj['namespace']
            page_name = page_name_obj['page_name']

            # Filter for pages in the "Data" namespace.
            if namespace != self.DATA_NAMESPACE:
                continue

            file_path = DATA_PAGE_FILE_MAP.get(page_name)
            # If a file path is not defined for a page, log a warning.
            if file_path is None:
                if page_name not in IGNORE_PAGES:
                    logger.warning(f'Missing file map for data page "{page_name}". Either add a corresponding file path or add it to the ignore list')
                continue

            data = json_utils.read(f'{self.OUTPUT_DIR}/{file_path}', ignore_error=True)
            if data is None:
                logger.warning(f'Missing data for page "{page_name}": {file_path}')
                return

            json_string = json.dumps(data, indent=4)
            self._update_page(page, json_string)

    def upload_new_page(self, title, content):
        """
        Uploads a page to the wiki if it doesn't already exist.

        Args:
            title (str): The full title of the page (e.g., "Update:May_27,_2025").
            content (str): The wikitext content for the page.
        """
        existing_titles = {t for _, t in self.wiki_updates}
        normalized_title = title.replace('_', ' ')
        if normalized_title in existing_titles:
            logger.trace(f'Page "{title}" already exists, skipping creation.')
            return

        logger.info(f'Creating new page: "{title}"')
        if self.dry_run:
            return

        page = self.site.pages[title]
        page.save(content, summary=self.upload_message)
        logger.success(f'Successfully saved page "{title}"')

    def _update_latest_chain(self):
        """
        Updates the linked list of updates on the wiki by setting next_update on the previous page.

        Queries the wiki to find the most recent update page that is strictly earlier
        than the current patch and links it forward. This ensures the chain is correctly maintained
        even if intermediate update pages were created manually on the wiki.

        Determines the latest changelog by reading changelog_configs.json (which holds full
        history) rather than scanning wikitext files in the output folder.
        """
        # Read changelog configs to find the latest entry (holds full history metadata)
        changelog_configs_path = os.path.join(self.OUTPUT_DIR, 'changelogs', 'changelog_configs.json')
        changelog_configs = json_utils.read(changelog_configs_path, ignore_error=True)
        if not changelog_configs:
            return

        # Filter out hero lab entries and entries without dates, then sort by date+variant
        update_ids = [f'{cid}.txt' for cid, cfg in changelog_configs.items() if cfg.get('date') and not cfg.get('is_hero_lab')]
        sorted_ids = changelog_utils.sort_changelog_files(update_ids)
        if not sorted_ids:
            return

        latest_id = sorted_ids[-1].replace('.txt', '')
        latest_date = changelog_utils.parse_changelog_date_from_id(latest_id)

        if not latest_date:
            logger.error(f'Could not parse date from {latest_id}, cannot update chain')
            return

        latest_page_title = f"Update:{latest_date.strftime('%B')}_{latest_date.day},_{latest_date.year}"

        # Use cached wiki updates from earlier fetch
        if not self.wiki_updates:
            logger.warning(f'No existing update pages found on wiki to link with {latest_page_title}')
            return

        # Filter for updates strictly earlier than the latest date
        earlier_updates = [(date, title) for date, title in self.wiki_updates if date < latest_date]

        if not earlier_updates:
            logger.info(f'No previous update found on wiki for {latest_page_title}')
            return

        # Get the most recent one among them (chronologically)
        earlier_updates.sort(key=lambda x: x[0])
        prev_date, prev_page_title = earlier_updates[-1]

        logger.info(f"Found previous update: {prev_page_title} (date: {prev_date.strftime('%Y-%m-%d')})")

        # Link the previous update to the latest one
        self._link_updates(prev_page_title, latest_page_title, prev_date, latest_date)

    def _link_updates(self, prev_title: str, next_title: str, prev_date: datetime, next_date: datetime):
        """
        Update the next_update field on prev_title to point to next_title.
        Uses regex to safely edit the wikitext without affecting other parameters.
        """
        page = self.site.pages[prev_title]
        if not page.exists:
            logger.warning(f'Previous page {prev_title} does not exist, cannot link')
            return

        current_text = page.text()

        # Create the link string: {{Update link|Month|Day|Year}}
        next_link_str = f"{{{{Update link|{next_date.strftime('%B')}|{next_date.day}|{next_date.year}}}}}"

        # Robust idempotency check: normalize whitespace and match the template
        # Handles extra spaces inside template like {{Update link | January | 29 | 2026 }}
        normalized_pattern = (
            r'\{\{\s*Update\s+link\s*\|\s*'
            + re.escape(next_date.strftime('%B'))
            + r'\s*\|\s*'
            + str(next_date.day)
            + r'\s*\|\s*'
            + str(next_date.year)
            + r'\s*\}\}'
        )
        if re.search(normalized_pattern, current_text):
            logger.trace(f'Page {prev_title} is already linked to next update {next_title}')
            return

        # Regex handles various whitespace patterns.
        # Pattern stops at newline followed by | (next parameter), newline followed by }} (end), or end of string.
        pattern = r'(\|\s*next_update\s*=[ \t]*)(.*?)(?=\n\||\n\}\}|\Z)'

        if not re.search(pattern, current_text, re.DOTALL):
            logger.warning(f"Could not find '| next_update =' parameter in {prev_title}")
            return

        new_text = re.sub(pattern, rf'\1{next_link_str}', current_text, count=1, flags=re.DOTALL)

        logger.info(f'Linking {prev_title} -> {next_title}')
        if not self.dry_run:
            page.save(new_text, summary=f"{self.upload_message}: Linking next update to {next_date.strftime('%Y-%m-%d')}")
            logger.success(f'Updated {prev_title}')

    def _update_page(self, page, updated_text):
        logger.info(f'Updating page: "{page.name}"')
        if self.dry_run:
            return

        page.save(updated_text, summary=self.upload_message, minor=False, bot=True)
        logger.success(f'Successfully updated page "{page.name}"')

    def _get_namespace_id(self, search_namespace):
        for namespace_id, namespace in self.site.namespaces.items():
            if namespace == search_namespace:
                return namespace_id

        raise Exception(f'Namespace {search_namespace} not found')

    def _split_page_name(self, full_page_name: str):
        """
        Retrieve namespace of page name, where full page name is formatted as '$NAMESPACE:$PAGE_NAME'
        """
        split_page = full_page_name.split(':')
        if len(split_page) != 2:
            return {'namespace': 'Main', 'page_name': full_page_name}

        return {'namespace': split_page[0], 'page_name': split_page[1]}
