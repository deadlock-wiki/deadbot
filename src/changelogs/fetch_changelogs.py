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
    Each record in changelogs.json
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

    # Hero lab changelogs need to be added manually to
    # ./input-data/raw-changelogs following the
    # naming convention 'herolab_2024_10_29.txt'
    # see the referenced file for example formatting

    # Then they need to be added to
    # /input-data/changelogs.json following
    # the same naming convention and formatted the same
    # as other changelogs, but with
    # "forum_id": null
    # "link": null

    def __init__(self, client_version, update_existing):
        self.changelogs: dict[str, ChangelogString] = {}
        self.changelog_configs: dict[str, ChangelogConfig] = {}
        self.client_version = client_version
        self.update_existing = update_existing
        self.localization_data_en = {}

    def load_localization(self, output_dir):
        self.localization_data_en = json_utils.read(os.path.join(output_dir, 'localizations', 'english.json'))

    def get_rss(self, rss_url):
        self.RSS_URL = rss_url
        self._fetch_forum_changelogs()

        return self.changelogs

    def get_txt(self, changelog_path):
        self._process_local_changelogs(changelog_path)
        return self.changelogs

    def changelogs_to_file(self, input_dir, output_dir):
        # Write raw changelog lines to files
        for version, changelog in self.changelogs.items():
            raw_output_dir = os.path.join(output_dir, 'raw')
            os.makedirs(raw_output_dir, exist_ok=True)
            path = raw_output_dir + f'/{version}.txt'
            if version == 'herolab_2024_10_24':
                print(changelog)
            with open(path, 'w', encoding='utf8') as f_out:
                f_out.write(changelog)

        # Write configuration data (such as all the different version id's,
        # forum link, and forum date) for the changelogs to 1 file

        # changelogs.json is not overwritten even when update_existing is True
        # many entries were initially manually added due to
        # only the first page on the site having rss feed

        # Read existing changelogs.json content,
        changelogs_path = output_dir + '/changelogs.json'
        existing_changelogs = json_utils.read(changelogs_path)

        # add any keys that are not yet present or have differing values,
        existing_changelogs.update(self.changelog_configs)

        # add ones from input-data's changelogs.json, which currently include hero lab changelogs
        input_changelogs = json_utils.read(os.path.join(input_dir, 'changelogs.json'))
        existing_changelogs.update(input_changelogs)

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

        first_iteration = True
        for key, value in changelogs.items():
            if key == 'Language':
                continue
            # key i.e. Citadel_PatchNotes_HeroLabs_hero_astro_1
            # value i.e. <b>10/24/2024</b>\t\t\t<li>Hero Added to Hero Labs<li>Changed from x to z</li>
            
            # Parse the date
            date = value.split('\t')[0].replace('<b>', '').replace('</b>', '')
            if len(date) > 10:
                date = date[:10]

            # Remove date from remaining string
            remaining_str = value.replace(f'<b>{date}</b>\t\t\t', '')

            # Reformat mm/dd/yyyy to yyyy_mm_dd
            date = date.split('/')
            date = f'{date[2]}_{date[0]}_{date[1]}'

            # Create the raw changelog id (used as filename in raw folder)
            # i.e. herolab_2024_10_29
            raw_changelog_id = f'herolab_{date.replace("/", "_")}'

            # Parse hero name
            hero_key = key.split('Citadel_PatchNotes_HeroLabs_')[1][:-2]
            hero_name_en = self._localize(hero_key)
            header = f'[ HeroLab {hero_name_en} ]'

            # Initialize the changelog entry
            # requires or first_iteration because the previous deadbot run may have
            # already parsed this changelog, loading it to memory
            # we want to overwrite it instead
            # this doesn't require update_existing parameter to be true
            # as if it did, it would require to refetch all forum changelogs too
            first_line_of_entry = False
            if self.changelogs.get(raw_changelog_id) is None or first_iteration:
                self.changelogs[raw_changelog_id] = ""
                first_line_of_entry = True

            # Add the header to the changelog entry
            self.changelogs[raw_changelog_id] += (not first_line_of_entry) * '\n' + header + '\n'

            # Parse description
            # Ensure the date was able to be removed and was in the correct format
            if len(remaining_str) == len(value):
                print("[WARN] Date format may be different than expected (mm/dd/yyyy), detected date is " + date)
            while len(remaining_str) > 0:
                # Find the next <li> tag
                li_start = remaining_str.find('<li>')
                if li_start == -1:
                    break
                li_end = remaining_str.find('<li>', li_start+len('<li>'))
                # if no more <li>'s, find the last </li>
                if li_end == -1:
                    li_end = remaining_str.find('</li>', li_start+len('<li>'))
                if li_end == -1:
                    raise ValueError(f'No closing </li> tag found in {key}')

                # Extract the description
                description = remaining_str[li_start + len('<li>'):li_end]

                # Remove the description from the remaining value
                remaining_str = remaining_str[li_end + len('<li>'):]

                # Remove any remaining tags
                tags_to_remove = ['<ul>', '</ul>', '<b>', '</b>', '<i>', '</i>']
                for tag in tags_to_remove:
                    description = description.replace(tag, '')

                # Add the changelog entry
                self.changelogs[raw_changelog_id] += f'- {description}\n'

            first_iteration = False

                
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
