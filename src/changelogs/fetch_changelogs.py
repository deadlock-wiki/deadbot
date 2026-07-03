import os
from loguru import logger
import requests
import hashlib
from utils import file_utils, json_utils
from typing import TypedDict, NotRequired
from .constants import STEAM_APP_ID, STEAM_NEWS_API_URL, STEAM_MIGRATION_DATE
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import mwclient


class ChangelogConfig(TypedDict):
    """
    Each record in changelog_configs.json
    Key is "changelog_id", default to source_id, differs for herolab changelogs
    """

    source_id: str  # Now stores the Steam GID
    date: str
    link: str
    is_hero_lab: bool
    title: NotRequired[str]
    steam_hash: NotRequired[str]
    was_edited: NotRequired[bool]


class ForumUpdate(TypedDict):
    """Represents a single update entry fetched from the Steam API"""

    version: str
    text: str
    link: str
    title: NotRequired[str]
    steam_hash: NotRequired[str]


class Hotfix(TypedDict):
    """Represents a hotfix section to be appended to an existing wiki page"""

    date: str
    text: str


class ChangelogString(TypedDict):
    """Each complete changelog in a <changelog_id>.json file"""

    changelog_string: str


class ChangelogFetcher:
    """
    Fetches changelogs from Steam Web API and game files and parses them into a dictionary
    """

    def __init__(self, update_existing, input_dir, output_dir, herolab_patch_notes_path):
        self.changelogs: dict[str, ChangelogString] = {}
        self.changelog_configs: dict[str, ChangelogConfig] = {}
        self.hotfixes: list[Hotfix] = []
        self.update_existing = update_existing
        self.localization_data_en = {}

        self.INPUT_DIR = input_dir
        self.OUTPUT_DIR = output_dir
        self.STEAM_NEWS_URL = STEAM_NEWS_API_URL
        self.APP_ID = STEAM_APP_ID

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

    def _bbcode_to_text(self, bbcode: str) -> str:
        """Converts Steam BBCode to plain text matching existing parser expectations."""
        text = bbcode.replace('\\[', '[').replace('\\]', ']')
        text = text.replace('[p]', '').replace('[/p]', '\n')

        # Handle lists explicitly before the catch-all
        text = re.sub(r'\[/?list\]', '', text)
        text = re.sub(r'\[\*\]', '- ', text)

        # Remove bold/italic/underline tags
        text = re.sub(r'\[/?b\]', '', text)
        text = re.sub(r'\[/?i\]', '', text)
        text = re.sub(r'\[/?u\]', '', text)

        # Handle links: [url=...]text[/url] -> text
        text = re.sub(r'\[url=[^\]]*\](.*?)\[/url\]', r'\1', text)
        text = re.sub(r'\[/?url\]', '', text)

        # Handle images, steam items, youtube
        text = re.sub(r'\[img[^\]]*\].*?\[/img\]', '', text)
        text = re.sub(r'\[steamitem[^\]]*\].*?\[/steamitem\]', '', text)
        text = re.sub(r'\[previewyoutube[^\]]*\].*?\[/previewyoutube\]', '', text)

        # Catch-all: remove any remaining BBCode tags we missed
        text = re.sub(r'\[/?[a-zA-Z0-9]+(?:\s[^\]]*)?\]', '', text)

        # Clean up extra blank lines
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    def run(self):
        self.load_localization()
        self.fetch_steam_changelogs()
        self.get_gamefile_changelogs()
        self.changelogs_to_file()

    def load_localization(self):
        self.localization_data_en = json_utils.read(os.path.join(self.OUTPUT_DIR, 'localizations', 'english.json'))

    def changelogs_to_file(self):
        """
        Save combined changelogs to input and output directories.
        Saving to input directory is necessary as the Steam API only provides
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

    def fetch_steam_changelogs(self):
        """Fetch patch notes from Steam Web API."""
        logger.trace('Fetching Steam news for changelogs')
        target_tz = ZoneInfo('US/Pacific')

        try:
            resp = requests.get(self.STEAM_NEWS_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f'Failed to fetch Steam news: {e}')
            return

        news_items = data.get('appnews', {}).get('newsitems', [])
        updates_by_day: dict[str, list[ForumUpdate]] = defaultdict(list)

        for item in news_items:
            tags = item.get('tags', [])
            if 'patchnotes' not in tags:
                logger.trace(f"Skipping non-patch-note news: {item.get('title')} (Tags: {tags})")
                continue

            gid = str(item['gid'])
            url = item.get('url') or f'https://store.steampowered.com/news/app/{self.APP_ID}/view/{gid}'
            title = item.get('title', '')
            date_unix = item['date']
            contents_bbcode = item.get('contents', '')

            dt_utc = datetime.fromtimestamp(date_unix, tz=ZoneInfo('UTC'))
            dt_valve = dt_utc.astimezone(target_tz)
            post_date = dt_valve.strftime('%Y-%m-%d')

            # Only process patch notes on or after 2026-06-04.
            # Before this date, changelogs were sourced from the Deadlock forums and
            # already exist in the data directory. Overwriting them with Steam-sourced
            # content would replace forum URLs and formatting, which is undesirable.
            if post_date < STEAM_MIGRATION_DATE:
                logger.trace(f'Skipping old patch note before 2026-06-04: {title}')
                continue

            logger.trace(f'Processing Steam patch note: {title} ({post_date})')
            text = self._bbcode_to_text(contents_bbcode)
            steam_hash = hashlib.md5(contents_bbcode.encode('utf-8')).hexdigest()

            updates_by_day[post_date].append({'version': gid, 'text': text, 'link': url, 'title': title, 'steam_hash': steam_hash})

        for date_key, entries in updates_by_day.items():
            changelog_id = date_key

            local_path = os.path.join(self.INPUT_DIR, 'changelogs/raw', f'{changelog_id}.txt')
            local_content = file_utils.read(local_path) if os.path.exists(local_path) else ''

            wiki_content = self._get_wiki_content(changelog_id) if not local_content else ''

            existing_config = self.changelog_configs.get(changelog_id)

            main_entry = None
            append_entries = []

            if existing_config:
                matched = False
                for e in entries:
                    if e['version'] == existing_config.get('source_id'):
                        main_entry = e
                        matched = True
                        if existing_config.get('steam_hash') and existing_config['steam_hash'] != e['steam_hash']:
                            logger.warning(f'Steam post for {date_key} was edited by the devs!')
                            self.changelog_configs[changelog_id] = {
                                'source_id': e['version'],
                                'date': date_key,
                                'link': e['link'],
                                'is_hero_lab': False,
                                'title': e.get('title'),
                                'steam_hash': e['steam_hash'],
                                'was_edited': True,
                            }
                            break
                if existing_config and self.changelog_configs.get(changelog_id, {}).get('was_edited'):
                    continue

                if not matched and entries:
                    main_entry = entries[0]

                for e in entries:
                    if e != main_entry:
                        append_entries.append(e)
            else:
                entries.sort(key=lambda x: x['version'])
                main_entry = entries[0]
                append_entries = entries[1:]

            if local_content:
                current_text = local_content
            elif wiki_content and main_entry:
                logger.info(f'Found wiki page for {date_key} without local file, appending new content')
                append_entries.insert(0, main_entry)
                current_text = wiki_content
                main_entry = None
            else:
                current_text = main_entry['text'] if main_entry else (self.changelogs.get(changelog_id, ''))

            old_text = local_content or wiki_content or ''

            def get_next_patch_num(txt):
                matches = re.findall(r'=== Patch (\d+) ===', txt)
                if matches:
                    return max(map(int, matches)) + 1
                return 2 if txt.strip() else 1

            final_text = current_text
            for entry in append_entries:
                entry_text = entry['text']
                entry_text = re.sub(r'=== Patch \d+ ===\n*', '', entry_text).strip()

                normalized_entry = re.sub(r'^- ', '* ', entry_text, flags=re.MULTILINE)
                normalized_final = re.sub(r'^- ', '* ', final_text, flags=re.MULTILINE)
                if normalized_entry not in normalized_final:
                    patch_num = get_next_patch_num(final_text)
                    final_text += f'\n\n=== Patch {patch_num} ===\n\n{entry_text}'
                    logger.debug(f'Adding Patch {patch_num} to {date_key}')

            potential_headers = re.findall(r'=== Patch \d+ ===', final_text)
            for h in potential_headers:
                if h not in old_text:
                    section_text = self._get_patch_section(h, final_text)
                    if section_text:
                        self.hotfixes.append({'date': date_key, 'text': section_text})
                        logger.debug(f'Detected hotfix: {h} for {date_key}')

            self.changelogs[changelog_id] = final_text

            if main_entry:
                source_id = main_entry['version']
                link = main_entry['link']
                title = main_entry.get('title')
                steam_hash = main_entry.get('steam_hash')
            elif existing_config:
                source_id = existing_config.get('source_id')
                link = existing_config.get('link')
                title = existing_config.get('title')
                steam_hash = existing_config.get('steam_hash')
            elif append_entries:
                source_id = append_entries[0]['version']
                link = append_entries[0]['link']
                title = append_entries[0].get('title')
                steam_hash = append_entries[0].get('steam_hash')
            else:
                source_id = None
                link = None
                title = None
                steam_hash = None

            self.changelog_configs[changelog_id] = {
                'source_id': source_id,
                'date': date_key,
                'link': link,
                'is_hero_lab': False,
                'title': title,
                'steam_hash': steam_hash,
            }

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
                        'source_id': None,
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
