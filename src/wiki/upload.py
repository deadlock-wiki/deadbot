import os
import mwclient
import json
from datetime import datetime
from utils import json_utils, game_utils, meta_utils
from .pages import DATA_PAGE_FILE_MAP, IGNORE_PAGES
from loguru import logger


class WikiUpload:
    """
    Uploads a set of specified data to deadlock.wiki via the MediaWiki API
    """

    def __init__(self, output_dir, dry_run=False):
        self.OUTPUT_DIR = output_dir
        self.DATA_NAMESPACE = 'Data'

        if dry_run:
            logger.info('Wiki upload is running in dry-run mode. No changes will be made to the wiki.')
        self.dry_run = dry_run

        game_version = game_utils.load_game_info(f'{self.OUTPUT_DIR}/version.txt')['ClientVersion']
        deadbot_version = meta_utils.get_deadbot_version()
        self.upload_message = f'Deadbot v{deadbot_version}-{game_version}'

        self.auth = {
            'user': os.environ.get('BOT_WIKI_USER'),
            'password': os.environ.get('BOT_WIKI_PASS'),
        }

        if not self.auth['user']:
            raise Exception('BOT_WIKI_USER env var is required to upload to wiki')

        if not self.auth['password']:
            raise Exception('BOT_WIKI_PASS env var is required to upload to wiki')

        self.site = mwclient.Site('deadlock.wiki', path='/')
        self.site.login(self.auth['user'], self.auth['password'])

    def run(self):
        logger.info(f'Uploading Data to Wiki - {self.upload_message}')
        self._update_data_pages()
        self._upload_changelog_pages()

    def _upload_changelog_pages(self):
        """
        Reads formatted changelog files and uploads them to the wiki.
        """
        changelog_dir = os.path.join(self.OUTPUT_DIR, 'changelogs', 'wiki')
        if not os.path.isdir(changelog_dir):
            logger.trace(f'Changelog wiki directory not found at "{changelog_dir}", skipping changelog upload.')
            return

        logger.info('Uploading changelog pages...')
        for filename in sorted(os.listdir(changelog_dir)):
            if not filename.endswith('.txt'):
                continue

            changelog_id = filename.replace('.txt', '')
            try:
                # Changelog IDs are typically 'YYYY-MM-DD' or 'YYYY-MM-DD-1'.
                # We only care about the date part for the page title.
                date_part = '-'.join(changelog_id.split('-')[:3])
                date_obj = datetime.strptime(date_part, '%Y-%m-%d')

                wiki_date_str = f"{date_obj.strftime('%B')}_{date_obj.day},_{date_obj.year}"
                page_title = f'Update:{wiki_date_str}'

                filepath = os.path.join(changelog_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.upload_new_page(page_title, content)

            except ValueError:
                logger.error(f"Could not parse date from changelog filename '{filename}'. Skipping.")
            except Exception as e:
                logger.error(f"Failed to upload changelog from '{filename}': {e}")

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
        page = self.site.pages[title]
        if page.exists:
            logger.trace(f'Page "{title}" already exists, skipping creation.')
            return

        logger.info(f'Creating new page: "{title}"')
        if self.dry_run:
            return

        page.save(content, summary=self.upload_message)
        logger.success(f'Successfully created page "{title}"')

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
