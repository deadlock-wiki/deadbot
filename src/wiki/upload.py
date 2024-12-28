import os
import mwclient
import json
from utils import json_utils, game_utils, meta_utils
from .pages import DATA_PAGE_FILE_MAP, IGNORE_PAGES, CHANGELOGS_PAGE_DIR, CHANGELOGS_PAGE_DEST
from loguru import logger


class WikiUpload:
    """
    Uploads a set of specified data to deadlock.wiki via the MediaWiki API
    """

    def __init__(self, output_dir):
        self.OUTPUT_DIR = output_dir
        self.DATA_NAMESPACE = 'Data'

        game_version = game_utils.load_game_info(f'{self.OUTPUT_DIR}/version.txt')['ClientVersion']
        deadbot_version = meta_utils.get_deadbot_version()
        self.upload_message = f'DeadBot v{deadbot_version}-{game_version}'

        logger.info('Uploading Data to Wiki -', self.upload_message)

        self.auth = {
            'user': os.environ.get('BOT_WIKI_USER'),
            'password': os.environ.get('BOT_WIKI_PASS'),
        }

        if not self.auth['user']:
            raise Exception('BOT_WIKI_USER env var is required to upload to wiki')

        if not self.auth['password']:
            raise Exception('BOT_WIKI_PASS env var is required to upload to wiki')

        self.site = mwclient.Site('deadlocked.wiki', path='/')
        self.site.login(self.auth['user'], self.auth['password'])

        changelog_map = self._create_changelog_map(CHANGELOGS_PAGE_DIR, CHANGELOGS_PAGE_DEST)
        print(changelog_map)
        self.data_pages_map = DATA_PAGE_FILE_MAP
        for page_dest, changelog_file in changelog_map.items():
            self.data_pages_map[page_dest] = changelog_file

    def update_data_pages(self):
        namespace_id = self._get_namespace_id(self.DATA_NAMESPACE)
        for page in self.site.allpages(namespace=namespace_id):
            page_name_obj = self._split_page_name(page.name)
            namespace = page_name_obj['namespace']
            page_name = page_name_obj['page_name']

            # filter for the "Data" namespace, as that is where all generated data lives on the wiki
            if namespace != self.DATA_NAMESPACE:
                print(f'Skipping page "{page.name}" as it is not in the Data namespace')
                continue

            file_path = self.data_pages_map.get(page_name)
            # If file is not found in either page map or ignore list, add a warning to resolve that
            if file_path is None:
                if page_name not in IGNORE_PAGES:
                    logger.warning(
                        f'[WARN] Missing file map for data page "{page_name}".'
                        'Either add a corresponding file path or add it to the ignore list'
                    )
                continue

            data = json_utils.read(f'{self.OUTPUT_DIR}/{file_path}')
            json_string = json.dumps(data, indent=4)
            self._update_page(page, json_string)

    def _create_changelog_map(self, changelog_page_dir, changelog_page_dest):
        changelog_map = {}
        for version in os.listdir(os.path.join(self.OUTPUT_DIR, changelog_page_dir)):
            changelog_file = os.path.join(changelog_page_dir, version)
            page_dest = changelog_page_dest.replace('<version>', version.split('.json')[0])
            changelog_map[page_dest] = changelog_file
            
        return changelog_map

    def _update_page(self, page, updated_text):
        success_msg = f'Page "{page.name}" updated'
        print(success_msg)
        return
        if page.text() != updated_text:
            page.save(updated_text, summary=self.upload_message, minor=False, bot=True)
            logger.success(success_msg)

    def _get_namespace_id(self, search_namespace):
        for namespace_id, namespace in self.site.namespaces.items():
            if namespace == search_namespace:
                return namespace_id

        raise Exception(f'Namespace {search_namespace} not found')

    def _split_page_name(self, full_page_name: str):
        """
        Retrieve namespace of page name, where full page name is formatted as 
        '$NAMESPACE:$PAGE_NAME'
        or
        '$PAGE_NAME' for the main namespace
        """
        split_page = full_page_name.split(':')
        if len(split_page) != 2:
            return {'namespace': 'Main', 'page_name': full_page_name}

        return {'namespace': split_page[0], 'page_name': split_page[1]}
