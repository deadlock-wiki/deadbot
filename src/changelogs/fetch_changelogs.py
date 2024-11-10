import os
from os import listdir
from os.path import isfile, join
from loguru import logger
import feedparser
from bs4 import BeautifulSoup
from urllib import request
from utils import json_utils
from typing import TypedDict


class Changelog(TypedDict):
    """
    Each record in changelogs.json
    Key is "changelod_id", default to forum_id, differs for herolab changelogs
    """

    forum_id: str
    date: str
    link: str


class ChangelogLine(TypedDict):
    """Each changelog line in a <changelog_id>.json file"""

    Description: str
    Tags: list[str]


class ChangelogFetcher:
    """
    Fetches changelogs from the deadlock forums and parses them into a dictionary
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

    def __init__(self):
        self.changelog_lines: dict[str, ChangelogLine] = {}
        self.changelogs: dict[str, Changelog] = {}

    def get_rss(self, rss_url, update_existing=False):
        self.RSS_URL = rss_url
        self._fetch_forum_changelogs(update_existing)

        return self.changelog_lines

    def get_txt(self, changelog_path):
        self._process_local_changelogs(changelog_path)
        return self.changelog_lines

    def changelogs_to_file(self, input_dir, output_dir):
        # Write raw changelog lines to files
        for version, changelog in self.changelog_lines.items():
            raw_output_dir = os.path.join(output_dir, 'raw')
            os.makedirs(raw_output_dir, exist_ok=True)
            with open(raw_output_dir + f'/{version}.txt', 'w', encoding='utf8') as f_out:
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
        existing_changelogs.update(self.changelogs)

        # add ones from input-data's changelogs.json, which currently include hero lab changelogs
        input_changelogs = json_utils.read(os.path.join(input_dir, 'changelogs.json'))
        existing_changelogs.update(input_changelogs)

        # Sort the keys by the date lexicographically
        # null dates will be at the end
        keys = list(existing_changelogs.keys())
        keys.sort(key=lambda x: existing_changelogs[x]['date'])
        self.changelogs = {key: existing_changelogs[key] for key in keys}

        # write back
        json_utils.write(changelogs_path, self.changelogs)

    def _fetch_update_html(self, link):
        html = request.urlopen(link).read()
        soup = BeautifulSoup(html, features='html.parser')
        entries = []
        # Find all <div> tags with class 'bbWrapper' (xenforo message body div)
        for div in soup.find_all('div', class_='bbWrapper'):
            entries.append(div.text.strip())
        return entries

    # download rss feed from changelog forum and parse entries
    def _fetch_forum_changelogs(self, update_existing=False):
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

            version = entry.link.split('.')[-1].split('/')[0]
            # Raise error if version isnt numerical
            try:
                int(version)
            except ValueError:
                raise ValueError(f'Version {version} must be numerical')
            if version is None or version == '':
                raise ValueError(f'Version {version} must not be blank/missing')

            if not update_existing and (version in self.changelog_lines.keys()):
                skip_num += 1
                continue
            try:
                full_text = '\n---\n'.join(self._fetch_update_html(entry.link))
            except Exception:
                print(f'Issue with parsing RSS feed item {entry.link}')

            self.changelog_lines[version] = full_text
            self.changelogs[version] = {'forum_id': version, 'date': date, 'link': entry.link}

        if skip_num > 0:
            logger.trace(f'Skipped {skip_num} RSS items that already exists')

    def _process_local_changelogs(self, changelog_path):
        logger.trace('Parsing Changelog txt files')
        # Make sure path exists
        if not os.path.isdir(changelog_path):
            print(f'Issue opening changelog dir `{changelog_path}`')
            return
        files = [f for f in listdir(changelog_path) if isfile(join(changelog_path, f))]
        logger.trace(f'Found {str(len(files))} changelog entries in `{changelog_path}`')
        for file in files:
            version = file.replace('.txt', '')
            try:
                with open(changelog_path + f'/{version}.txt', 'r', encoding='utf8') as f:
                    changelogs = f.read()
                    self.changelog_lines[version] = changelogs
            except Exception:
                print(f'Issue with {file}, skipping')
