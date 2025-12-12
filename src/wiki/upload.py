import os
import mwclient
import json
import re
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

        self.site = mwclient.Site('deadlock.wiki', path='/')

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

    def run(self):
        logger.info(f'Uploading Data to Wiki - {self.upload_message}')
        self._update_data_pages()
        self._upload_changelog_pages()
        self._update_latest_chain()

    def _upload_changelog_pages(self):
        """
        Reads formatted changelog files and uploads them to the wiki.
        """
        changelog_dir = os.path.join(self.OUTPUT_DIR, 'changelogs', 'wiki')
        if not os.path.isdir(changelog_dir):
            logger.trace(f'Changelog wiki directory not found at "{changelog_dir}", skipping changelog upload.')
            return

        logger.info('Uploading changelog pages...')

        # Get list of files and sort them to identify the absolute latest patch
        files = sorted([f for f in os.listdir(changelog_dir) if f.endswith('.txt')])
        if not files:
            return

        latest_filename = files[-1]  # The last file in the sorted list is the most recent

        recent_files = files[-10:]

        for filename in recent_files:
            changelog_id = filename.replace('.txt', '')
            try:
                # Changelog IDs are typically 'YYYY-MM-DD' or 'YYYY-MM-DD-1'.
                # We only care about the date part for the page title.
                parts = changelog_id.split('-')
                date_part = '-'.join(parts[:3])
                suffix = ''

                # If there is a 4th part (e.g. 2024-10-18-1)
                if len(parts) > 3:
                    suffix = f'_(Patch_{int(parts[3]) + 1})'

                date_obj = datetime.strptime(date_part, '%Y-%m-%d')

                wiki_date_str = f"{date_obj.strftime('%B')}_{date_obj.day},_{date_obj.year}{suffix}"
                page_title = f'Update:{wiki_date_str}'

                filepath = os.path.join(changelog_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Pass is_latest=True only for the most recent file
                self.upload_new_page(page_title, content, is_latest=(filename == latest_filename))

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

    def upload_new_page(self, title, content, is_latest=False):
        """
        Uploads a page to the wiki if it doesn't already exist or if content changed.
        If it exists and is_latest is True, check for smart append opportunities (hotfixes).
        """
        page = self.site.pages[title]
        if page.exists:
            current_content = page.text()
            if current_content.strip() == content.strip():
                logger.trace(f'Page "{title}" is up to date, skipping.')
                return
            else:
                # Only attempt smart append if this is the absolute latest patch
                if is_latest:
                    self._smart_append_hotfixes(page, current_content, content)
                else:
                    logger.trace(f'Page "{title}" exists and differs, but is not latest. Skipping to preserve history.')
        else:
            logger.info(f'Creating new page: "{title}"')
            if not self.dry_run:
                page.save(content, summary=self.upload_message)
                logger.success(f'Successfully saved page "{title}"')

    def _smart_append_hotfixes(self, page, current_text, new_generated_text):
        """
        Parses the new generated text for headers like "=== Patch X ===".
        If that header is missing from current_text, append that section
        to the end of the template.
        """
        # Regex to find sections starting with === Patch N ===
        # Captures Group 1: The Header
        # Captures Group 2: The Body (non-greedy until next header or end of string)
        patch_pattern = re.compile(r'(=== Patch \d+ ===)(.*?)(?=(=== Patch \d+ ===)|$)', re.DOTALL)

        new_patches = patch_pattern.finditer(new_generated_text)

        text_to_append = []
        found_new = False

        for match in new_patches:
            header = match.group(1).strip()  # === Patch 2 ===
            body = match.group(2).rstrip()

            # If this header does not exist in the live page
            if header not in current_text:
                logger.info(f"Found new hotfix section '{header}' missing from live page.")
                text_to_append.append(f'\n\n{header}{body}')
                found_new = True
            else:
                logger.trace(f"Hotfix section '{header}' already exists on page.")

        if not found_new:
            logger.info(f'Page {page.name} exists and has no new hotfix sections to append.')
            return

        # Append logic: Insert before the closing }} of the Update layout template
        if current_text.strip().endswith('}}'):
            # Remove the last brackets, add content, re-add brackets
            base_text = current_text.strip()

            # Check if it actually ends with }}
            if base_text[-2:] == '}}':
                formatted_append = ''.join(text_to_append)
                new_page_text = base_text[:-2] + formatted_append + '\n}}'

                logger.info(f'Appending {len(text_to_append)} new sections to {page.name}')
                if not self.dry_run:
                    page.save(new_page_text, summary='Deadbot: Appended new hotfix/patch notes')
                    logger.success(f'Successfully appended hotfixes to {page.name}')
            else:
                logger.warning(f"Page {page.name} does not end with '}}', cannot safely append hotfix.")
        else:
            logger.warning(f"Page {page.name} structure unrecognized (no closing '}}'), skipping append.")

    def _update_latest_chain(self):
        """
        Looks at the two most recent changelogs.
        Edits the 'next_update' field of the 2nd most recent patch
        to point to the most recent patch.
        Preserves all other content on the page.
        """
        changelog_dir = os.path.join(self.OUTPUT_DIR, 'changelogs', 'wiki')
        if not os.path.isdir(changelog_dir):
            return

        # Get all changelog files sorted by date
        # We rely on filenames YYYY-MM-DD.txt being naturally sortable
        files = sorted([f for f in os.listdir(changelog_dir) if f.endswith('.txt')])

        if len(files) < 2:
            return  # Need at least 2 updates to create a link

        # Identify the 'Previous' (Dec 3) and 'Latest' (Dec 16)
        latest_file = files[-1]
        prev_file = files[-2]

        try:
            # Parse Latest (The Target)
            latest_id = latest_file.replace('.txt', '')
            parts = latest_id.split('-')
            date_part = '-'.join(parts[:3])
            latest_date = datetime.strptime(date_part, '%Y-%m-%d')

            # Create the string: {{Update link|December|16|2025}}
            # Double braces are needed for f-string escaping
            next_link_str = f"{{{{Update link|{latest_date.strftime('%B')}|{latest_date.day}|{latest_date.year}}}}}"

            # Parse Previous (The Page to Edit)
            prev_id = prev_file.replace('.txt', '')
            p_parts = prev_id.split('-')
            p_date_part = '-'.join(p_parts[:3])
            p_suffix = ''
            if len(p_parts) > 3:
                p_suffix = f'_(Patch_{int(p_parts[3]) + 1})'

            prev_date = datetime.strptime(p_date_part, '%Y-%m-%d')
            prev_page_title = f"Update:{prev_date.strftime('%B')}_{prev_date.day},_{prev_date.year}{p_suffix}"

        except ValueError as e:
            logger.error(f'Failed to parse dates for chaining: {e}')
            return

        # Fetch the existing page content for 'Previous'
        page = self.site.pages[prev_page_title]
        if not page.exists:
            logger.warning(f'Could not find previous page {prev_page_title} to link next update.')
            return

        current_text = page.text()

        # Check if it already has the link (idempotency)
        if next_link_str in current_text:
            logger.trace(f'Page {prev_page_title} is already linked to next update.')
            return

        # Surgical Edit using Regex
        # Look for "| next_update =" followed by anything until a new line or pipe
        # We capture the key group (group 1) to preserve spacing/formatting
        pattern = r'(\|\s*next_update\s*=\s*)(.*?)(\n|\|)'

        # Function to ensure we don't accidentally overwrite if regex fails match
        if not re.search(pattern, current_text):
            logger.warning(f"Could not find '| next_update =' parameter in {prev_page_title}")
            return

        # Replace whatever was in next_update with our new link
        # \1 restores "| next_update = ", \3 restores the newline/pipe
        new_text = re.sub(pattern, f'\\1{next_link_str}\\3', current_text, count=1)

        logger.info(f'Linking {prev_page_title} -> {next_link_str}')

        if not self.dry_run:
            page.save(new_text, summary=f"Deadbot: Linking next update to {latest_date.strftime('%Y-%m-%d')}")
            logger.success(f'Updated {prev_page_title} with next link.')

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
