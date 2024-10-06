import os
from os import listdir
from os.path import isfile, join
import feedparser
from bs4 import BeautifulSoup
from urllib import request


class ChangelogFetcher:
    def __init__(self):
        self.changelogs_by_date = {}

    def get_rss(self, rss_url):
        self.RSS_URL = rss_url
        self._fetch_forum_changelogs()
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
    def _fetch_forum_changelogs(self):
        print('Parsing Changelog RSS feed')
        # fetches 20 most recent entries
        feed = feedparser.parse(self.RSS_URL)
        for entry in feed.entries:
            # Dependent on thread title being in the format "mm-dd-yyyy Update"
            date = entry.title.replace(' Update', '')
            full_text = '\n---\n'.join(self._fetch_update_html(entry.link))
            self.changelogs_by_date[date] = full_text

    def _process_local_changelogs(self, changelog_path):
        print('Parsing Changelog txt files')
        files = [f for f in listdir(changelog_path) if isfile(join(changelog_path, f))]
        print(f'Found {str(len(files))} changelog entries in `{changelog_path}`')
        for file in files:
            date = file.replace('.txt', '')
            with open(changelog_path + f'/{date}.txt', 'r', encoding='utf8') as f:
                changelogs = f.read()
                self.changelogs_by_date[date] = changelogs
