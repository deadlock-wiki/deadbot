import os
from os import listdir
from os.path import isfile, join
from loguru import logger
import feedparser
from bs4 import BeautifulSoup
from urllib import request
from urllib.parse import urlparse
from utils import file_utils, json_utils
from typing import TypedDict
from .constants import CHANGELOG_RSS_URL
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import mwclient


class ChangelogConfig(TypedDict):
    """
    Each record in changelog_configs.json
    Key is "changelog_id", default to forum_id, differs for herolab changelogs
    """

    forum_id: str
    date: str
    link: str


class ForumUpdate(TypedDict):
    """Represents a single update entry fetched from the forum"""

    version: str
    text: str
    link: str


class Hotfix(TypedDict):
    """Represents a hotfix section to be appended to an existing wiki page"""

    date: str
    text: str


class ChangelogString(TypedDict):
    """Each complete changelog in a <changelog_id>.json file"""

    changelog_string: str


class ChangelogFetcher:
    """
    Fetches changelogs from the deadlock forums and game files and parses them into a dictionary
    """

    def __init__(self, update_existing, input_dir, output_dir, herolab_patch_notes_path):
        self.changelogs: dict[str, ChangelogString] = {}
        self.changelog_configs: dict[str, ChangelogConfig] = {}
        self.hotfixes: list[Hotfix] = []
        self.update_existing = update_existing
        self.localization_data_en = {}

        self.INPUT_DIR = input_dir
        self.OUTPUT_DIR = output_dir
        self.RSS_URL = CHANGELOG_RSS_URL

        # Safely derive base url (e.g., https://forums.playdeadlock.com)
        parsed_url = urlparse(self.RSS_URL)
        self.FORUM_BASE_URL = f'{parsed_url.scheme}://{parsed_url.netloc}'

        self.HEROLABS_PATCH_NOTES_PATH = herolab_patch_notes_path

        self.TAGS_TO_REMOVE = ['<ul>', '</ul>', '<b>', '</b>', '<i>', '</i>']

        self.wiki_site = None

        self._load_input_data()

    def _load_input_data(self):
        """Load input changelog data into the fetcher"""
        path = f'{self.INPUT_DIR}/changelogs/changelog_configs.json'
        existing_changelogs = json_utils.read(path)
        self.changelog_configs = existing_changelogs

        # load 'changelogs/raw/<changelog_id>.txt' files
        all_files = os.listdir(f'{self.INPUT_DIR}/changelogs/raw')
        for file in all_files:
            raw_changelog = file_utils.read(f'{self.INPUT_DIR}/changelogs/raw/{file}')
            changelog_id = file.replace('.txt', '')
            self.changelogs[changelog_id] = raw_changelog

    def _get_existing_content(self, date_key: str) -> str:
        """
        Get existing changelog content from available sources.
        Checks local files first (fastest), then wiki if available.

        Args:
            date_key: Date in YYYY-MM-DD format

        Returns:
            str: Existing content or empty string if none found
        """
        # 1. Check local input files first (no API calls needed)
        local_path = os.path.join(self.INPUT_DIR, 'changelogs/raw', f'{date_key}.txt')
        if os.path.exists(local_path):
            content = file_utils.read(local_path)
            if content:
                logger.trace(f'Using local file content for {date_key}')
                return content

        # 2. Check wiki page content if local file doesn't exist
        content = self._get_wiki_content(date_key)
        if content:
            logger.info(f'Using wiki page content for {date_key}')
            return content

        # 3. No existing content found
        return ''

    def _get_wiki_content(self, date_key: str) -> str:
        """
        Fetch existing changelog content from wiki page.
        Returns empty string if page doesn't exist or wiki not available.

        Args:
            date_key: Date in YYYY-MM-DD format

        Returns:
            str: Notes content from wiki page or empty string
        """
        if self.wiki_site is None:
            try:
                self.wiki_site = mwclient.Site('deadlock.wiki', path='/')
                logger.info('Connected to wiki for changelog fetching (read-only)')
            except Exception as e:
                logger.warning(f'Could not connect to wiki: {e}. Will only check local files.')
                return ''

        try:
            date_obj = datetime.strptime(date_key, '%Y-%m-%d')
            # Format: Update:February_12,_2026
            page_title = f"Update:{date_obj.strftime('%B')}_{date_obj.day},_{date_obj.year}"

            page = self.wiki_site.pages[page_title]
            if not page.exists:
                return ''

            page_text = page.text()

            # Extract just the notes section (the actual changelog content)
            pattern = r'\|\s*notes\s*=\s*(.*?)(?:\n\}\}|\Z)'
            match = re.search(pattern, page_text, re.DOTALL)
            if match:
                notes_content = match.group(1).strip()

                # Only strip specific icons the bot auto-generates.
                # This turns {{HeroIcon|Hero}} -> Hero, so the parser can re-wrap it later.
                notes_content = re.sub(r'\{\{(?:Hero|Item|Ability)Icon\|([^}]+)\}\}', r'\1', notes_content)

                logger.debug(f'Found existing wiki page for {date_key}')
                return notes_content

            return ''

        except Exception as e:
            logger.trace(f'Could not fetch wiki content for {date_key}: {e}')
            return ''

    def _normalize_text_for_comparison(self, text: str) -> str:
        """Strip formatting differences to allow comparison between wiki and forum text"""
        # Strip icon templates
        text = re.sub(r'\{\{(?:Hero|Item|Ability)Icon\|([^}]+)\}\}', r'\1', text)
        # Strip bullet points
        text = re.sub(r'^\s*[*\-]\s+', '', text, flags=re.MULTILINE)
        # Normalize whitespace
        text = '\n'.join(line.strip() for line in text.splitlines())
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    def _get_patch_section(self, header: str, full_text: str) -> str:
        """
        Extract a specific patch section from changelog text.

        Args:
            header: Patch header like "=== Patch 2 ==="
            full_text: Complete changelog text

        Returns:
            str: The patch section including header, or empty string if not found
        """
        pattern = re.compile(rf'({re.escape(header)})(.*?)(?=(=== Patch \d+ ===)|$)', re.DOTALL)
        match = pattern.search(full_text)
        return match.group(0).strip() if match else ''

    def run(self):
        self.load_localization()
        self.fetch_forum_changelogs()
        self.get_gamefile_changelogs()
        self.changelogs_to_file()

    def load_localization(self):
        self.localization_data_en = json_utils.read(os.path.join(self.OUTPUT_DIR, 'localizations', 'english.json'))

    def get_txt(self, changelog_path):
        self._process_local_changelogs(changelog_path)
        return self.changelogs

    def changelogs_to_file(self):
        """
        Save combined changelogs to input and output directories.
        Saving to input directory is necessary as the RSS feed can only see
        recent changelogs.

        Since output data is paved over each deploy, we need this source for historic
        changelog data.
        """

        # Sort the keys by the date lexicographically
        # null dates will be at the end
        keys = list(self.changelog_configs.keys())
        keys.sort(key=lambda x: self.changelog_configs[x]['date'])
        self.changelog_configs = {key: self.changelog_configs[key] for key in keys}

        raw_output_dir = os.path.join(self.OUTPUT_DIR, 'changelogs/raw')
        raw_input_dir = os.path.join(self.INPUT_DIR, 'changelogs/raw')

        for changelog_id, changelog in self.changelogs.items():
            os.makedirs(raw_output_dir, exist_ok=True)

            file_utils.write(f'{raw_output_dir}/{changelog_id}.txt', changelog)
            file_utils.write(f'{raw_input_dir}/{changelog_id}.txt', changelog)

        json_utils.write(f'{self.OUTPUT_DIR}/changelogs/changelog_configs.json', self.changelog_configs)
        json_utils.write(f'{self.INPUT_DIR}/changelogs/changelog_configs.json', self.changelog_configs)

        # Save decoupled hotfixes for the uploader
        json_utils.write(f'{self.OUTPUT_DIR}/changelogs/hotfixes.json', self.hotfixes)

    def _fetch_update_html(self, link):
        """
        Fetches the HTML content of a forum link and extracts posts grouped by date.
        Returns:
            dict: { 'YYYY-MM-DD': [ {'text': str, 'link': str}, ... ] }
        """
        html = request.urlopen(link).read()
        soup = BeautifulSoup(html, features='html.parser')

        # Dictionary to group posts by date string 'YYYY-MM-DD'
        content_by_date = defaultdict(list)

        # XenForo posts are wrapped in <article class="message ...">
        articles = soup.find_all('article', class_='message')

        # Target Timezone: Valve HQ (US/Pacific)
        target_tz = ZoneInfo('US/Pacific')

        for i, article in enumerate(articles):
            # Extract the Date
            time_elem = article.find('time', class_='u-dt')
            if not time_elem or not time_elem.has_attr('datetime'):
                continue

            try:
                dt_str = time_elem['datetime']
                # Parse ISO string (e.g. 2024-11-21T01:00:00+0000)
                dt_utc = datetime.fromisoformat(dt_str)
                # Convert to Valve HQ time
                dt_valve = dt_utc.astimezone(target_tz)
                post_date = dt_valve.strftime('%Y-%m-%d')
            except (IndexError, KeyError, ValueError) as e:
                logger.warning(f'Failed to parse date from post: {e}')
                continue

            # Extract the Link
            if i == 0:
                # The first post found is the Main Thread.
                # Use the canonical link passed into the function (e.g. /threads/update.123/)
                post_link = link
            else:
                # For subsequent posts (comments/hotfixes), find the specific permalink
                post_link = None
                attribution = article.find('ul', class_='message-attribution-main')
                if attribution:
                    a_tag = attribution.find('a', href=True)
                    if a_tag:
                        href = a_tag['href']
                        if href.startswith('http'):
                            post_link = href
                        else:
                            # Join base and relative path ensuring exactly one slash
                            post_link = self.FORUM_BASE_URL.rstrip('/') + '/' + href.lstrip('/')

                # Fallback if extraction fails
                if not post_link:
                    post_link = link

            # Extract the Content
            content_div = article.find('div', class_='bbWrapper')
            if not content_div:
                continue

            text = content_div.text.strip()
            if text:
                content_by_date[post_date].append({'text': text, 'link': post_link})

        return content_by_date

    def get_gamefile_changelogs(self):
        """Read and parse the Hero Labs changelogs in the game files"""
        changelogs = json_utils.read(self.HEROLABS_PATCH_NOTES_PATH)

        gamefile_changelogs = dict()

        # Iterate each pair in the patch note localization
        for key, string in changelogs.items():
            # Not a real patch note
            if key == 'Language':
                continue

            # key i.e. Citadel_PatchNotes_HeroLabs_hero_astro_1
            # string i.e. "<b>10/24/2024</b>\t\t\t
            #   <li>Hero Added to Hero Labs<li>
            #   Changed y from x to z</li>"

            # Parse the date from the beginning of the string
            date_raw = string.split('\t')[0].replace('<b>', '').replace('</b>', '')
            if len(date_raw) > 10:
                date_raw = date_raw[:10]

            # Remove date from remaining string
            remaining_str = string.replace(f'<b>{date_raw}</b>\t\t\t', '')

            # Reformat mm/dd/yyyy to yyyy-mm-dd
            date = format_date(date_raw)

            # Parse hero name to create a header for the changelog entry
            # Citadel_PatchNotes_HeroLabs_hero_astro_1 ->
            # hero_astro ->
            # Holliday ->
            # [ HeroLab Holliday ]
            hero_key = key.split('Citadel_PatchNotes_HeroLabs_')[1][:-2]
            hero_name_en = self._localize(hero_key)
            header = f'[ HeroLab {hero_name_en} ]'

            # Initialize the changelog entry if its the first line for this hero's patch (version)
            # Create the raw changelog id (used as filename in raw folder)
            # i.e. 2024-10-29_HeroLab
            raw_changelog_id = f'{date.replace("/", "-")}_HeroLab'
            if raw_changelog_id not in gamefile_changelogs:
                gamefile_changelogs[raw_changelog_id] = header + '\n'
            else:
                gamefile_changelogs[raw_changelog_id] += '\n' + header + '\n'

            # Ensure the date was able to be removed and was in the correct format
            if len(remaining_str) == len(string):
                logger.warning(f'Date format may not have been able to be parsed correctly for {date}')

            # Parse full description by accumulating each description separated by <li> tags
            # <li>Text 1<li>Text 2</li> -> Text 1\nText 2\n
            while len(remaining_str) > 0:
                # Parse the next description
                description, remaining_str = self._parse_description(remaining_str)
                if description is None:
                    break

                # Add to the current changelog entry
                gamefile_changelogs[raw_changelog_id] += f'- {description}\n'

                # Add the config entry if it doesn't exist
                if raw_changelog_id not in self.changelog_configs:
                    self.changelog_configs[raw_changelog_id] = {
                        'forum_id': None,
                        'date': date,
                        'link': None,
                        'is_hero_lab': True,
                    }
        self.changelogs.update(gamefile_changelogs)

    def _parse_description(self, string):
        # Find the next <li> tag
        li_start, li_end = self._find_li_tags(string)
        if li_start == -1:
            # No more list elements to be found
            return None, string
        if li_end == -1:
            raise ValueError(f'No closing </li> tag found in description {string}')

        # Extract the description
        description = string[li_start + len('<li>') : li_end]

        # Remove the description from the remaining string
        string = string[li_end + len('<li>') :]

        # Remove any remaining tags that are unneeded
        for tag in self.TAGS_TO_REMOVE:
            description = description.replace(tag, '')

        return description, string

    def _find_li_tags(self, string):
        # Find the next <li> tag
        li_start = string.find('<li>')

        # If no list elements are found, return right away
        if li_start == -1:
            return li_start, -1

        # Find the next li tag, which will either be <li>, or </li>
        li_end = string.find('<li>', li_start + len('<li>'))
        # if no more <li>'s, find the last </li>
        if li_end == -1:
            li_end = string.find('</li>', li_start + len('<li>'))

        return li_start, li_end

    def _localize(self, key):
        value = self.localization_data_en.get(key, None)
        if value is None:
            raise Exception(f'Localized string not found for key {key}')
        return value

    def fetch_forum_changelogs(self):
        """download rss feed from changelog forum and save all available entries"""
        logger.trace('Parsing Changelog RSS feed')
        # fetches 20 most recent entries
        feed = feedparser.parse(self.RSS_URL)

        # Bucket to collect all updates grouped by date
        updates_by_day: dict[str, list[ForumUpdate]] = defaultdict(list)

        for entry in feed.entries:
            # Parse version ID from URL
            version = entry.link.split('.')[-1].split('/')[0]
            try:
                int(version)
            except ValueError:
                try:
                    version = entry.link.split('/')[-2].split('.')[-1]
                    int(version)
                except ValueError:
                    continue

            if version is None or version == '':
                continue

            try:
                # Scrape this thread for date-grouped posts
                thread_updates = self._fetch_update_html(entry.link)
            except Exception as e:
                logger.error(f'Issue with parsing RSS feed item {entry.link}: {e}')
                continue

            # Add these updates to our master bucket
            for date_key, posts in thread_updates.items():
                # Join text if multiple posts exist within ONE thread for ONE day
                text_parts = []
                for i, p in enumerate(posts):
                    content = p['text']
                    if i > 0:
                        content = f'=== Patch {i + 1} ===\n{content}'
                    text_parts.append(content)

                full_text = '\n\n'.join(text_parts)
                specific_link = posts[0]['link']

                updates_by_day[date_key].append({'version': version, 'text': full_text, 'link': specific_link})

        # Now process the gathered updates day by day
        for date_key, entries in updates_by_day.items():
            changelog_id = date_key

            # Check for existing content from ANY source (local or wiki)
            old_text = self._get_existing_content(changelog_id)

            existing_config = self.changelog_configs.get(changelog_id)

            main_entry = None
            append_entries = []

            # Find the main entry
            if existing_config:
                for e in entries:
                    if e['version'] == existing_config['forum_id']:
                        main_entry = e
                        break
                for e in entries:
                    if e != main_entry:
                        append_entries.append(e)
            else:
                entries.sort(key=lambda x: x['version'])
                main_entry = entries[0]
                append_entries = entries[1:]

            # If we have existing content and new content is different,
            # treat it as an append rather than a replacement
            if old_text and main_entry:
                old_normalized = self._normalize_text_for_comparison(old_text)
                main_normalized = self._normalize_text_for_comparison(main_entry['text'])
                main_text_clean = re.sub(r'=== Patch \d+ ===\n*', '', main_entry['text']).strip()
                main_clean_normalized = self._normalize_text_for_comparison(main_text_clean)

                if main_normalized not in old_normalized and main_clean_normalized not in old_normalized:
                    logger.info(f'Detected new forum content for existing page {date_key}, treating as append')
                    # Move main_entry to append_entries since we already have base content
                    append_entries.insert(0, main_entry)
                    current_text = old_text
                    main_entry = None
                else:
                    current_text = main_entry['text'] if main_entry else old_text
            else:
                # Set Base Text
                current_text = main_entry['text'] if main_entry else (self.changelogs.get(changelog_id, ''))

            # Helper to get next patch number
            def get_next_patch_num(txt):
                matches = re.findall(r'=== Patch (\d+) ===', txt)
                if matches:
                    return max(map(int, matches)) + 1
                # If there's existing content but no patches yet, this will be Patch 2
                return 2 if txt.strip() else 1

            # Merge any secondary entries into current text with proper patch headers
            final_text = current_text
            for entry in append_entries:
                # Remove any existing patch headers from the entry first
                entry_text = entry['text']
                entry_text = re.sub(r'=== Patch \d+ ===\n*', '', entry_text).strip()

                entry_normalized = self._normalize_text_for_comparison(entry_text)
                final_normalized = self._normalize_text_for_comparison(final_text)

                if entry_normalized not in final_normalized:
                    patch_num = get_next_patch_num(final_text)
                    final_text += f'\n\n=== Patch {patch_num} ===\n\n{entry_text}'
                    logger.debug(f'Adding Patch {patch_num} to {date_key}')

            # Detect hotfixes - compare new patches against old content
            potential_headers = re.findall(r'=== Patch \d+ ===', final_text)
            for h in potential_headers:
                if h not in old_text:
                    section_text = self._get_patch_section(h, final_text)
                    if section_text:
                        self.hotfixes.append({'date': date_key, 'text': section_text})
                        logger.debug(f'Detected hotfix: {h} for {date_key}')

            # Save to memory and update config
            self.changelogs[changelog_id] = final_text

            self.changelog_configs[changelog_id] = {
                'forum_id': main_entry['version']
                if main_entry
                else existing_config.get('forum_id')
                if existing_config
                else append_entries[0]['version']
                if append_entries
                else None,
                'date': date_key,
                'link': main_entry['link']
                if main_entry
                else existing_config.get('link')
                if existing_config
                else append_entries[0]['link']
                if append_entries
                else None,
                'is_hero_lab': False,
            }

    def _process_local_changelogs(self, changelog_path):
        logger.trace('Parsing Changelog txt files')
        # Make sure path exists
        if not os.path.isdir(changelog_path):
            logger.warning(f'Issue opening changelog dir `{changelog_path}`')
            return
        files = [f for f in listdir(changelog_path) if isfile(join(changelog_path, f))]
        logger.trace(f'Found {str(len(files))} changelog entries in `{changelog_path}`')
        for file in files:
            version = file.replace('.txt', '')
            try:
                with open(changelog_path + f'/{version}.txt', 'r', encoding='utf8') as f:
                    changelogs = f.read()
                    self.changelogs[version] = changelogs
            except Exception:
                logger.warning(f'Issue with {file}, skipping')

    def _create_changelog_id(self, date, forum_id, i=0):
        """
        Creating a custom id based on the date by appending _<i>
        if its another patch for the same day, i.e.:
        2024-10-29
        2024-10-29-1
        2024-10-29-2
        """

        # (2024-12-17, 0) -> 2024-12-17
        # (2024-12-17, 1) -> 2024-12-17-1
        id = date if i == 0 else f'{date}-{i}'

        # Existing config for this date
        existing_config = self.changelog_configs.get(id, None)

        # If this id doesn't yet exist, use it
        if existing_config is None:
            return id
        # Else same date already exists

        # If the forum id is the same, use the same changelog id
        # which will update the existing record
        if existing_config['forum_id'] == forum_id:
            return id
        # Else forum id's are different, so different patches on the same day

        # Recursively check if the next id is available
        return self._create_changelog_id(date, forum_id, i + 1)


def format_date(date):
    """
    Reformat mm/dd/yyyy or mm-dd-yyyy to yyyy-mm-dd
    Also convert days and months to 2 digits
    """
    # Split date by / or -
    if '/' in date:
        date = date.split('/')
    elif '-' in date:
        date = date.split('-')
    else:
        raise ValueError(f'Invalid date format {date}')

    # If the day or month is a single digit, add a leading 0
    for i in range(2):
        if len(date[i]) == 1:
            date[i] = '0' + date[i]

    # Reformat to yyyy-mm-dd
    date = f'{date[2]}-{date[0]}-{date[1]}'
    return date
