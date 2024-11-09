import os
import mwclient
from utils import json_utils
from .pages import PAGE_FILE_MAP


class WikiUpload:
    """
    Uploads a set of specified data to deadlock.wiki via the MediaWiki API
    """

    def __init__(self, output_dir):
        self.OUTPUT_DIR = output_dir
        self.DATA_NAMESPACE = 'Data'
        self.upload_message = 'DeadBot vx.xx buildyyyyy'
        self.auth = {
            'user': os.environ.get('BOT_WIKI_USER'),
            'password': os.environ.get('BOT_WIKI_PASS'),
        }

        self.edit_counter = 0

        site = mwclient.Site('deadlocked.wiki', path='/')
        site.login(self.auth['user'], self.auth['password'])

        # filter for the "Data" namespace, as that is where all generated data lives on the wiki
        self.data_pages = [
            page for page in site.pages if self._get_namespace(page.name) == self.DATA_NAMESPACE
        ]

    def update_data_pages(self):
        for page in self.data_pages:
            file_path = PAGE_FILE_MAP.get(page.name)
            if file_path is None:
                continue

            file = json_utils.read(f'{self.OUTPUT_DIR}/{file_path}')
            print('Updating page', file)
            # self._update_page(page)

    def _update_page(self, page, updated_text):
        page.save(updated_text, summary=self.upload_message)
        print(f"Page '{page.name}' updated")

    def _get_namespace(self, full_page_name: str):
        """
        Retrieve namespace of page name, where full page name is formatted as '$NAMESPACE:$PAGE_NAME'
        """
        split_page = full_page_name.split(':')
        if len(split_page) != 2:
            return

        return split_page[0]

    def _page_has_category(page, category_name):
        for category in page.categories():
            if category.name == category_name:
                return True

        return False
