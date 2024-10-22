import os
from os import listdir
from os.path import isfile, join
import feedparser
from bs4 import BeautifulSoup
from urllib import request
from utils import json_utils


class ChangelogFetcher:
    def __init__(self):
        self.changelogs_by_version = {}
        #layer1: version # as assigned by developers
        #layer2: content (reworked in another pr, not gonna bother writing temporary 
        # stuff here for layer2-4)

        self.changelog_date_links = {}
        #layer1: version # as assigned by developers
        #layer2: date

    def get_rss(self, rss_url, update_existing=False):
        self.RSS_URL = rss_url
        self._fetch_forum_changelogs(update_existing)

        return self.changelogs_by_version

    def get_txt(self, changelog_path):
        self._process_local_changelogs(changelog_path)
        return self.changelogs_by_version

    def changelogs_to_file(self, output_dir):
        for version, changelog in self.changelogs_by_version.items():
            raw_output_dir = os.path.join(output_dir, 'raw')
            os.makedirs(raw_output_dir, exist_ok=True)
            with open(raw_output_dir + f'/{version}.txt', 'w', encoding='utf8') as f_out:
                f_out.write(changelog)

        # Read existing changelogs.json content, 
        # add any keys that are not yet present or have differing values, 
        # write back

        # this file is not overwritten even when update_existing is True
        # many entries were manually added due to only the first page on the site has rss feed
        changelogs_path = output_dir + '/changelogs.json'
        existing_changelogs = json_utils.read(changelogs_path)
        existing_changelogs.update(self.changelog_date_links)
        
        # Sort existing_changelogs by key but numerically
        keys = list(existing_changelogs.keys())
        # Sort the keys numerically, not lexiconically
        keys.sort(key=lambda x: int(x))
        self.changelog_date_links =  {key: existing_changelogs[key] for key in keys}

        json_utils.write(changelogs_path, self.changelog_date_links)

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
                date = date[:len(date_format)]

            version = entry.link.split('.')[-1].split('/')[0]
            # Raise error if version isnt numerical
            try:
                int(version)
            except ValueError:
                raise ValueError(f'Version {version} must be numerical')
            if version is None or version == '':
                raise ValueError(f'Version {version} must not be blank/missing')
            
            if not update_existing and (version in self.changelogs_by_version.keys()):
                skip_num += 1
                continue
            try:
                full_text = '\n---\n'.join(self._fetch_update_html(entry.link))
            except Exception:
                print(f'Issue with parsing RSS feed item {entry.link}')
            if version == None or version == '':
                print(date, entry.link)

            self.changelogs_by_version[version] = full_text
            self.changelog_date_links[version] = {'date': date, 'link': entry.link}

        if skip_num > 0:
            print(f'Skipped {skip_num} RSS items that already exists')

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
                    self.changelogs_by_version[version] = changelogs
            except Exception:
                print(f'Issue with {file}, skipping')
