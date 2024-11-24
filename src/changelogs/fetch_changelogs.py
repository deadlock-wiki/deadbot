import os
from os import listdir
from os.path import isfile, join
import feedparser
from bs4 import BeautifulSoup
from urllib import request
from utils import json_utils
from typing import TypedDict


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

    def __init__(self, update_existing):
        self.changelogs: dict[str, ChangelogString] = {}
        self.changelog_configs: dict[str, ChangelogConfig] = {}
        self.update_existing = update_existing
        self.localization_data_en = {}

        self.TAGS_TO_REMOVE = ['<ul>', '</ul>', '<b>', '</b>', '<i>', '</i>']

    def load_localization(self, output_dir):
        self.localization_data_en = json_utils.read(
            os.path.join(output_dir, 'localizations', 'english.json')
        )

    def get_rss(self, rss_url):
        self.RSS_URL = rss_url
        self._fetch_forum_changelogs()

        return self.changelogs

    def get_txt(self, changelog_path):
        self._process_local_changelogs(changelog_path)
        return self.changelogs

    def changelogs_to_file(self, output_dir):
        # Write raw changelog lines to files
        for version, changelog in self.changelogs.items():
            raw_output_dir = os.path.join(output_dir, 'raw')
            os.makedirs(raw_output_dir, exist_ok=True)
            path = raw_output_dir + f'/{version}.txt'
            with open(path, 'w', encoding='utf8') as f_out:
                f_out.write(changelog)

        # Write configuration data (such as all the different version id's,
        # forum link, and forum date) for the changelogs to 1 file

        # changelog_configs.json is not overwritten even when update_existing is True
        # many entries were initially manually added due to
        # only the first page on the site having rss feed
        changelogs_path = output_dir + '/changelog_configs.json'
        if not os.path.isfile(changelogs_path):
            # Create the directory and file if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            json_utils.write(changelogs_path, self.changelog_configs)
        else:
            # Read existing changelog_configs.json content,
            existing_changelogs = json_utils.read(changelogs_path)

            # add any keys that are not yet present or have differing values,
            existing_changelogs.update(self.changelog_configs)

            # Sort the keys by the date lexicographically
            # null dates will be at the end
            keys = list(existing_changelogs.keys())
            keys.sort(key=lambda x: existing_changelogs[x]['date'])
            self.changelog_configs = {key: existing_changelogs[key] for key in keys}

            # write back
            json_utils.write(changelogs_path, self.changelog_configs)

    def _fetch_update_html(self, link):
        html = request.urlopen(link).read()
        soup = BeautifulSoup(html, features='html.parser')
        entries = []
        # Find all <div> tags with class 'bbWrapper' (xenforo message body div)
        for div in soup.find_all('div', class_='bbWrapper'):
            entries.append(div.text.strip())
        return entries

    def get_gamefile_changelogs(self, changelog_path):
        # only english are retrieved
        changelogs = json_utils.read(changelog_path)

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

            # Reformat mm/dd/yyyy to yyyy_mm_dd
            date = format_date(date)

            # Create the raw changelog id (used as filename in raw folder)
            # i.e. herolab_2024_10_29.json
            raw_changelog_id = f'herolab_{date.replace("/", "_")}'

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
                print(
                    '[WARN] Date format may not have been able to be parsed '
                    + 'correctly to (yyyy_mm_dd), parsed date is '
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

    # download rss feed from changelog forum and parse entries
    def _fetch_forum_changelogs(self):
        print('Parsing Changelog RSS feed')
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
                print(f'Issue with parsing RSS feed item {entry.link}')

            self.changelogs[version] = full_text
            self.changelog_configs[version] = {'forum_id': version, 'date': date, 'link': entry.link}

        if skip_num > 0:
            print(f'Skipped {skip_num}/{len(feed.entries)} RSS items that already exists')

    def _process_local_changelogs(self, changelog_path):
        print('Parsing Changelog txt files')
        # Make sure path exists
        if not os.path.isdir(changelog_path):
            print(f'Issue opening changelog dir `{changelog_path}`')
            return
        files = [f for f in listdir(changelog_path) if isfile(join(changelog_path, f))]
        print(f'Found {str(len(files))} changelog entries in `{changelog_path}`')
        for file in files:
            version = file.replace('.txt', '')
            try:
                with open(changelog_path + f'/{version}.txt', 'r', encoding='utf8') as f:
                    changelogs = f.read()
                    self.changelogs[version] = changelogs
            except Exception:
                print(f'Issue with {file}, skipping')


def format_date(date):
    """
    Reformat mm/dd/yyyy or mm-dd-yyyy to yyyy_mm_dd
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

    # Reformat to yyyy_mm_dd
    date = f'{date[2]}_{date[0]}_{date[1]}'
    return date
