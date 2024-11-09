import os
import mwclient
import json
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

        self.site = mwclient.Site('deadlocked.wiki', path='/')
        self.site.login(self.auth['user'], self.auth['password'])

    def update_data_pages(self):
        for page in self.site.pages:
            page_name_obj = self._split_page_name(page.name)
            namespace = page_name_obj['namespace']
            page_name = page_name_obj['page_name']

            # filter for the "Data" namespace, as that is where all generated data lives on the wiki
            if namespace != self.DATA_NAMESPACE:
                continue

            file_path = PAGE_FILE_MAP.get(page_name)
            if file_path is None:
                print(f'[WARN] Missing file map for data page "{page_name}"')
                continue

            data = json_utils.read(f'{self.OUTPUT_DIR}/{file_path}')
            json_string = json.dumps(data, indent=4)
            self._update_page(page, json_string)

    def _update_page(self, page, updated_text):
        page.save(updated_text, summary=self.upload_message)
        print(f"Page '{page.name}' updated")

    def _split_page_name(self, full_page_name: str):
        """
        Retrieve namespace of page name, where full page name is formatted as '$NAMESPACE:$PAGE_NAME'
        """
        split_page = full_page_name.split(':')
        if len(split_page) != 2:
            return {'namespace': 'Main', 'page_name': full_page_name}

        return {'namespace': split_page[0], 'page_name': split_page[1]}
