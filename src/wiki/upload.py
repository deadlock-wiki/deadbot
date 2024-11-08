import os
import mwclient
from utils import pages


class WikiUpload:
    """
    Uploads a set of specified data to deadlock.wiki via the MediaWiki API
    """

    def __init__(self):
        self.auth = {
            'user': os.environ.get('BOT_WIKI_USER'),
            'password': os.environ.get('BOT_WIKI_PASS'),
        }

        self.edit_counter = 0

        site = mwclient.Site('deadlocked.wiki', path='/')
        site.login(self.auth.user, self.auth.password)

        self.attribute_pages = [
            page for page in site.pages if pages.page_has_category(page, 'Category:Attribute')
        ]

    def push_lane(self):
        for page in self.attribute_pages:
            self._update_page(page)

    def _update_page(self, page):
        updated_text = 'all the stats'

        # Save the page with the updated content
        if self.edit_counter != 0:
            page.save(updated_text, summary='DeadBot auto-update')
            print(f"Page '{page.name}' updated - {self.edit_counter} new changes")
        else:
            print(f"No changes made to '{page.name}'")

    def _page_has_category(page, category_name):
        for category in page.categories():
            if category.name == category_name:
                return True

        return False
