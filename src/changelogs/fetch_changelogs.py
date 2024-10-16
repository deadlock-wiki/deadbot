import os
from os import listdir
from os.path import isfile, join
import feedparser
from bs4 import BeautifulSoup
from urllib import request


class ChangelogFetcher:
    def __init__(self):
        self.changelogs_by_date = {}

    def get_rss(self, rss_url, update_existing = False):
        self.RSS_URL = rss_url
        self._fetch_forum_changelogs(update_existing)
        return self.changelogs_by_date

    def get_txt(self, changelog_path):
        self._process_local_changelogs(changelog_path)
        return self.changelogs_by_date

    def changelogs_to_file(self, output_dir):
        for date, changelog in self.changelogs_by_date.items():
            os.makedirs(output_dir, exist_ok=True)
            with open(output_dir + f'/{date}.txt', 'w', encoding='utf8') as f_out:
                f_out.write(changelog)

    def _fetch_update_html(self, link):
        html = request.urlopen(link).read()
        soup = BeautifulSoup(html, features='html.parser')
        entries = []
        # Find all <div> tags with class 'bbWrapper' (xenforo message body div)
        for div in soup.find_all('div', class_='bbWrapper'):
            entries.append(div.text.strip())
        return entries

    # download rss feed from changelog forum and parse entries
    def _fetch_forum_changelogs(self, update_existing = False):
        print('Parsing Changelog RSS feed')
        # fetches 20 most recent entries
        feed = feedparser.parse(self.RSS_URL)
        skip_num = 0
        for entry in feed.entries:
            # Dependent on thread title being in the format "mm-dd-yyyy Update"
            date = entry.title.replace(' Update', '')
            # Only update the existing if it doesn't already exist in the dict
            if not update_existing and (date in self.changelogs_by_date.keys()):
                skip_num += 1
                continue
            try:
                full_text = '\n---\n'.join(self._fetch_update_html(entry.link))
            except Exception:
                print(f'Issue with parsing RSS feed item {entry.link}')
            self.changelogs_by_date[date] = full_text
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
            date = file.replace('.txt', '')
            try:
                with open(changelog_path + f'/{date}.txt', 'r', encoding='utf8') as f:
                    changelogs = f.read()
                    self.changelogs_by_date[date] = changelogs
            except Exception:
                print(f'Issue with {file}, skipping')
