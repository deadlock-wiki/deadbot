import os
from os import isfile, listdir, join
from html.parser import HTMLParser
import feedparser
from bs4 import BeautifulSoup
from requests import urlopen


class HTMLTagRemover(HTMLParser):
    # https://www.slingacademy.com/article/python-ways-to-remove-html-tags-from-a-string#Using_HTMLParser
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_data(self, data):
        self.result.append(data)

    def get_text(self):
        return ''.join(self.result)


class ChangelogFetcher:
    def __init__(
        self,
        output_dir,
        txt_path=os.path.join(os.path.dirname(__file__), '../raw-changelogs/'),
        rss_feed='https://forums.playdeadlock.com/forums/changelog.10/index.rss',
    ):
        self.CHANGELOGS_DIR = txt_path
        self.OUTPUT_CHANGELOGS = output_dir + '/raw-changelogs'
        self.changelogs_by_date = {}

        return self.fetch_changelogs(self, txt=txt_path, rss=rss_feed)

    def fetch_update_html(link):
        html = urlopen(link).read()
        soup = BeautifulSoup(html, features='html.parser')
        entries = []
        # Find all <div> tags with class 'bbWrapper' (xenforo message body div)
        for div in soup.find_all('div', class_='bbWrapper'):
            html_remover = HTMLTagRemover()
            html_remover.feed(div.get_text())
            entries.append(html_remover.get_text())
        return entries

    # download rss feed from changelog forum and parse entries
    def fetch_forum_changelogs(self, f_url):
        print('Fetching Changelog RSS feed')
        # fetches 20 most recent entries
        feed = feedparser.parse(f_url)
        out_dir = self.OUTPUT_CHANGELOGS + '/rss'
        if len(feed.entries) > 0:
            os.makedirs(out_dir, exist_ok=True)
        for entry in feed.entries:
            # Dependent on thread title being in the format "mm-dd-yyyy Update"
            date = entry.title.replace(' Update', '')
            full_text = self.fetch_update_html(entry.link).join('\n---\n')
            self.changelogs_by_date[date] = full_text

    def process_local_changelogs(self):
        files = [f for f in listdir(self.CHANGELOGS_DIR) if isfile(join(self.CHANGELOGS_DIR, f))]
        out_dir = self.OUTPUT_CHANGELOGS + '/txt'
        if len(files) > 0:
            os.makedirs(out_dir, exist_ok=True)
        for file in files:
            date = file.replace('.txt', '')
            with open(self.CHANGELOGS_DIR + f'{date}.txt', 'r', encoding='utf8') as f:
                changelogs = f.read()
                self.changelogs_by_date[date] = changelogs
                with open(self.CHANGELOGS_DIR + f'txt/{date}.txt', 'r', encoding='utf8') as f_out:
                    f_out.write(changelogs)

    def fetch_changelogs(self, txt_path, rss_feed):
        self.changelogs_by_date = {}
        if txt_path:
            self.process_local_changelogs(txt_path)
        if rss_feed:
            self.fetch_forum_changelogs(rss_feed)
        return self.changelogs_by_date
