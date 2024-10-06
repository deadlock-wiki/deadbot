import os
from os import listdir
from os.path import isfile, join
import feedparser
from bs4 import BeautifulSoup
from urllib import request


class ChangelogFetcher:
    def __init__(
        self,
        txt_path=None,
        rss_feed=None,
    ):
        self.CHANGELOGS_DIR = txt_path
        self.RSS_URL = rss_feed
        self.changelogs_by_date = {}

    def fetch_changelogs(self):
        self.changelogs_by_date = {}
        if self.RSS_URL:
            self._fetch_forum_changelogs()
        # Since txt files run last, they will overwrite any rss logs with matching dates
        if self.CHANGELOGS_DIR:
            self._process_local_changelogs()
        return self.changelogs_by_date
    
    def changelogs_to_file(self, output_dir):
        for date, changelog in self.changelogs_by_date.items():
            os.makedirs(output_dir + '/changelogs/raw', exist_ok=True)
            with open(output_dir + f'/changelogs/raw/{date}.txt', 'w', encoding='utf8') as f_out:
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

    def _process_local_changelogs(self):
        print('Parsing Changelog txt files')
        files = [f for f in listdir(self.CHANGELOGS_DIR) if isfile(join(self.CHANGELOGS_DIR, f))]
        for file in files:
            date = file.replace('.txt', '')
            with open(self.CHANGELOGS_DIR + f'{date}.txt', 'r', encoding='utf8') as f:
                changelogs = f.read()
                self.changelogs_by_date[date] = changelogs
