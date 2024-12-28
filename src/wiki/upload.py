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

    def run(self):
        data_pages_to_update_map = self._get_pages_to_update_map()

        test = True
        if test:
            testing_pages = {'changelogs/versions/test.json': 'Changelog Test.json'}    
            self._update_data_pages(testing_pages)
        else:
            self._update_data_pages(data_pages_to_update_map)
        

    def _get_pages_to_update_map(self):
        """Retrieves a dict mapping json files to their corresponding wiki pages"""
        changelog_map = self._create_changelog_map(CHANGELOGS_PAGE_DIR, CHANGELOGS_PAGE_DEST)
        
        data_pages_map = DATA_PAGE_FILE_MAP
        for page_dest, changelog_file in changelog_map.items():
            data_pages_map[page_dest] = changelog_file
        
        return data_pages_map

    def _update_data_pages(self, data_pages_map):
        """Updates wiki data pages with their new data"""
        for file_path, page_name in data_pages_map.items():
            # Ensure the file exists
            full_file_path = os.path.join(self.OUTPUT_DIR, file_path)
            if not os.path.exists(full_file_path):
                logger.warning(f"File '{full_file_path}' does not exist, skipping wiki upload of page {page_name}")
                continue

            # Edit the page with the new content
            page_obj = self.site.pages[f'{self.DATA_NAMESPACE}:{page_name}']
            new_content_dict = json_utils.read(full_file_path)
            new_content_str = json.dumps(new_content_dict, indent=4)
            self._edit_page(page_obj, new_content_str)


    def _create_changelog_map(self, changelog_page_dir, changelog_page_dest):
        """Creates a dict mapping all changelog json files to their corresponding wiki pages"""
        changelog_map = {}
        for version in os.listdir(os.path.join(self.OUTPUT_DIR, changelog_page_dir)):
            changelog_file = os.path.join(changelog_page_dir, version)
            page_dest = changelog_page_dest.replace('<version>', version.split('.json')[0])
            changelog_map[changelog_file] = page_dest
            
        return changelog_map

    def _edit_page(self, page, updated_text):
        """Edits a wiki page or creates a new one with json content model if it doesn't exist"""
        page_exists = page.exists
        page_contentmodel = page.contentmodel
        
        def save_page(page, updated_text):
            page.save(text=updated_text, 
                      contentmodel='json', 
                      summary=self.upload_message, minor=False, bot=True)
        
        if page_exists:
            current_text = page.text().strip('\n')
            if page_contentmodel != 'json':
                logger.warning(f"Existing page '{page.name}' has content model '{page_contentmodel}'"+
                                   " instead of 'json', changing it to json before uploading.")
                save_page(page, updated_text)
            
            if current_text != updated_text.strip('\n'):
                logger.success(f"Edited page '{page.name}'")
            else:
                logger.trace(f'No changes detected for "{page.name}"')
        else:
            save_page(page, updated_text)
            logger.success(f"Created new page '{page.name}' with 'json' content model")