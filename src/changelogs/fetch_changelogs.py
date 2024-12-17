import os
from os import listdir
from os.path import isfile, join
from loguru import logger
import feedparser
from bs4 import BeautifulSoup
from urllib import request
from utils import file_utils, json_utils
from typing import TypedDict
from .constants import CHANGELOG_RSS_URL
import shutil


class ChangelogConfig(TypedDict):
    """
    Each record in changelog_configs.json
    Key is "changelod_id", default to forum_id, differs for herolab changelogs
    """

    forum_id: str
    date: str
    link: str


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
        self.update_existing = update_existing
        self.localization_data_en = {}

        self.INPUT_DIR = input_dir
        self.OUTPUT_DIR = output_dir
        self.RSS_URL = CHANGELOG_RSS_URL
        self.HEROLABS_PATCH_NOTES_PATH = herolab_patch_notes_path

        self.TAGS_TO_REMOVE = ['<ul>', '</ul>', '<b>', '</b>', '<i>', '</i>']
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

    def run(self):
        self.load_localization()
        self.fetch_forum_changelogs()
        self.get_gamefile_changelogs()
        self.changelogs_to_file()

    def load_localization(self):
        self.localization_data_en = json_utils.read(
            os.path.join(self.OUTPUT_DIR, 'localizations', 'english.json')
        )

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

        json_utils.write(
            f'{self.OUTPUT_DIR}/changelogs/changelog_configs.json', self.changelog_configs
        )
        json_utils.write(
            f'{self.INPUT_DIR}/changelogs/changelog_configs.json', self.changelog_configs
        )

    def _fetch_update_html(self, link):
        html = request.urlopen(link).read()
        soup = BeautifulSoup(html, features='html.parser')
        entries = []
        # Find all <div> tags with class 'bbWrapper' (xenforo message body div)
        for div in soup.find_all('div', class_='bbWrapper'):
            entries.append(div.text.strip())
        return entries

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
            date = string.split('\t')[0].replace('<b>', '').replace('</b>', '')
            if len(date) > 10:
                date = date[:10]

            # Remove date from remaining string
            remaining_str = string.replace(f'<b>{date}</b>\t\t\t', '')

            # Reformat mm/dd/yyyy to yyyy-mm-dd
            date = format_date(date)

            # Create the raw changelog id (used as filename in raw folder)
            # i.e. 2024-10-29_HeroLab
            raw_changelog_id = f'{date.replace("/", "-")}_HeroLab'

            # Parse hero name to create a header for the changelog entry
            # Citadel_PatchNotes_HeroLabs_hero_astro_1 ->
            # hero_astro ->
            # Holliday ->
            # [ HeroLab Holliday ]
            hero_key = key.split('Citadel_PatchNotes_HeroLabs_')[1][:-2]
            hero_name_en = self._localize(hero_key)
            header = f'[ HeroLab {hero_name_en} ]'

            # Initialize the changelog entry if its the first line for this hero's patch (version)
            if raw_changelog_id not in gamefile_changelogs:
                gamefile_changelogs[raw_changelog_id] = header + '\n'
            else:
                gamefile_changelogs[raw_changelog_id] += '\n' + header + '\n'

            # Ensure the date was able to be removed and was in the correct format
            if len(remaining_str) == len(string):
                logger.warning(
                    'Date format may not have been able to be parsed '
                    + 'correctly to (yyyy-mm-dd), parsed date is '
                    + date
                )

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
        return self.localization_data_en.get(key, None)

    def fetch_forum_changelogs(self):
        """download rss feed from changelog forum and save all available entries"""
        logger.trace('Parsing Changelog RSS feed')
        # fetches 20 most recent entries
        feed = feedparser.parse(self.RSS_URL)
        skip_num = 0
        for entry in feed.entries:
            # Dependent on thread title being in the format "mm-dd-yyyy Update"
            date = entry.title.replace(' Update', '')

            # Restrict to first 10 chars "10-18-2024 2" to "10-18-2024"
            date_format = 'mm-dd-yyyy'
            if len(date) > len(date_format):
                date = date[: len(date_format)]
            date = format_date(date)

            version = entry.link.split('.')[-1].split('/')[0]
            # Raise error if version isnt numerical
            try:
                int(version)
            except ValueError:
                raise ValueError(f'Version {version} must be numerical')
            if version is None or version == '':
                raise ValueError(f'Version {version} must not be blank/missing')

            if not self.update_existing and (version in self.changelogs.keys()):
                skip_num += 1
                continue
            try:
                full_text = '\n---\n'.join(self._fetch_update_html(entry.link))
            except Exception:
                logger.error(f'Issue with parsing RSS feed item {entry.link}')

            changelog_id = self._create_changelog_id(date, full_text)
            self.changelogs[changelog_id] = full_text
            self.changelog_configs[changelog_id] = {
                'forum_id': version,
                'date': date,
                'link': entry.link,
                'is_hero_lab': False,
            }

        if skip_num > 0:
            logger.trace(f'Skipped {skip_num} RSS items that already exists')

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

    def _create_changelog_id(self, date, changelog):
        """
        Creating a custom id based on the date by appending _<i> if the date already exists, i.e.
        2024-10-29-1
        2024-10-29-2
        2024-10-29-3
        """

        # Determine changelog_id
        changelog_id = date
        if date in self.changelogs:
            # If content already exists, we don't want to alter the changelog_id
            if changelog == self.changelogs[date]:
                return changelog_id

            # If both have very few lines, don't bother comparing further
            if not (len(changelog.split('\n')) < 5 and len(self.changelogs[date].split('\n')) < 5):
                # Determine what % of lines from one are in the other
                changelog_lines = changelog.split('\n')
                existing_lines = self.changelogs[date].split('\n')
                diff_percent = 1 - len(set(changelog_lines).intersection(existing_lines)) / len(
                    existing_lines
                )
                print(date, diff_percent)
                if diff_percent < 0.3:
                    print(
                        f'[WARN] Fetched changelog from date {date} was found to be very similar to '
                        + f'an existing changelog ({round(1-diff_percent,3)*100}% match) and has '
                        + 'been updated in input-data. Ensure it is just a '
                        + 'minor edit, and not a completely different changelog.'
                    )
                    return changelog_id
            # Otherwise 90% of chars differ or theres too few lines to compare

            # Content differs, so we need to use a series of changelog-id's
            # Remove the record under the base changelog_id and re-add it under <changelog_id>-1
            base_changelog = self.changelogs.pop(date)
            if f'{date}-1' not in self.changelogs:
                self.changelogs[f'{date}-1'] = base_changelog

        # Find the next available changelog_id in the series
        i = 1
        while f'{date}-{i}' in self.changelogs and changelog != self.changelogs[f'{date}-{i}']:
            i += 1

        return f'{date}-{i}'

    def _create_changelog_id(self, date, changelog):
        """
        Creating a custom id based on the date by appending _<i> if the date already exists, i.e.
        2024-10-29-1
        2024-10-29-2
        2024-10-29-3
        """

        # Determine changelog_id
        changelog_id = date
        if date in self.changelogs:
            # If content already exists, we don't want to alter the changelog_id
            if changelog == self.changelogs[date]:
                return changelog_id

            # If both have very few lines, don't bother comparing further
            if not (len(changelog.split('\n')) < 5 and len(self.changelogs[date].split('\n')) < 5):
                # Determine what % of lines from one are in the other
                changelog_lines = changelog.split('\n')
                existing_lines = self.changelogs[date].split('\n')
                diff_percent = 1 - len(set(changelog_lines).intersection(existing_lines)) / len(
                    existing_lines
                )
                print(date, diff_percent)
                if diff_percent < 0.3:
                    print(
                        f'[WARN] Fetched changelog from date {date} was found to be very similar to '
                        + f'an existing changelog ({round(1-diff_percent,3)*100}% match) and has '
                        + 'been updated in input-data. Ensure it is just a '
                        + 'minor edit, and not a completely different changelog.'
                    )
                    return changelog_id
            # Otherwise 90% of chars differ or theres too few lines to compare

            # Content differs, so we need to use a series of changelog-id's
            # Remove the record under the base changelog_id and re-add it under <changelog_id>-1
            base_changelog = self.changelogs.pop(date)
            if f'{date}-1' not in self.changelogs:
                self.changelogs[f'{date}-1'] = base_changelog

        # Find the next available changelog_id in the series
        i = 1
        while f'{date}-{i}' in self.changelogs and changelog != self.changelogs[f'{date}-{i}']:
            i += 1

        return f'{date}-{i}'


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
