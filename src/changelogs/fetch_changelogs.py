import os
from os import listdir
from os.path import isfile, join
import feedparser
from bs4 import BeautifulSoup
from urllib import request


class ChangelogFetcher:
    def __init__(
        self,
        output_dir,
        txt_path=None,
        rss_feed=None,
    ):
        self.CHANGELOGS_DIR = txt_path
        self.RSS_URL = rss_feed
        self.OUTPUT_CHANGELOGS = output_dir + '/raw-changelogs'
        self.changelogs_by_date = {}

    def fetch_changelogs(self):
        self.changelogs_by_date = {}
        if self.RSS_URL:
            self.fetch_forum_changelogs()
        # Since txt files run last, they will overwrite any rss logs with matching dates
        if self.CHANGELOGS_DIR:
            self.process_local_changelogs()
        return self.changelogs_by_date

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
        out_dir = self.OUTPUT_CHANGELOGS + '/rss'
        if len(feed.entries) > 0:
            os.makedirs(out_dir, exist_ok=True)
        for entry in feed.entries:
            # Dependent on thread title being in the format "mm-dd-yyyy Update"
            date = entry.title.replace(' Update', '')
            full_text = '\n---\n'.join(self.fetch_update_html(entry.link))
            self.changelogs_by_date[date] = full_text
            with open(out_dir + f'/{date}.txt', 'w', encoding='utf8') as f_out:
                f_out.write(full_text)

    def _process_local_changelogs(self):
        print('Parsing Changelog txt files')
        files = [f for f in listdir(self.CHANGELOGS_DIR) if isfile(join(self.CHANGELOGS_DIR, f))]
        out_dir = self.OUTPUT_CHANGELOGS + '/txt'
        if len(files) > 0:
            os.makedirs(out_dir, exist_ok=True)
        for file in files:
            date = file.replace('.txt', '')
            with open(self.CHANGELOGS_DIR + f'{date}.txt', 'r', encoding='utf8') as f:
                changelogs = f.read()
                self.changelogs_by_date[date] = changelogs
                with open(out_dir + f'/{date}.txt', 'w', encoding='utf8') as f_out:
                    f_out.write(changelogs)

