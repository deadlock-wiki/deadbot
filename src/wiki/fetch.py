import mwclient
from loguru import logger
from utils import json_utils


def fetch_page_list(output_path):
    """
    Fetches a list of all pages in the Main namespace (0) from the wiki
    and saves them to a JSON file.
    """
    logger.info('Connecting to deadlock.wiki to fetch page list...')

    try:
        site = mwclient.Site('deadlock.wiki', path='/')

        logger.trace('Fetching pages from Main namespace...')
        # mwclient handles pagination automatically via generator
        pages = site.allpages(namespace=0)

        # Convert generator to a list of strings
        page_titles = [page.name for page in pages]

        # Save to disk
        json_utils.write(output_path, page_titles)
        logger.success(f'Successfully saved {len(page_titles)} page titles to {output_path}')

    except Exception as e:
        logger.error(f'Failed to fetch page list: {e}')
