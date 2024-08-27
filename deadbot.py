import os
import re
import mwclient
from utils import json

'''
DeadBot pulls all aggregated data for heros, items ,buildings and more to populate
{{BotValue}} template data via the MediaWiki API

A DeadBot user has been created for this purpose, so the password will be needed
to run this locally. However local usage should be limited exclusively to testing
'''
class DeadBot:
    def __init__(self):
        self.out_dir = 'data-fetcher/output/'
        self.master_table = json.read(self.out_dir+'master-table.json')

        if len(self.master_table) == 0:
            raise Exception('master table is required to run the bot') 

        self.edit_counter = 0

        site = mwclient.Site(('https', 'deadlocked.wiki'), path='/')
        site.login('DeadBot', os.environ.get('BOT_WIKI_PASSWORD'))

        self.page_name = 'User:Saag/HeroTest'
        self.page = site.pages[self.page_name]
        self.text = self.page.text()


    def run(self):
        pattern = r"{{BotValue\|key=(.*?)\|value=(.*?)}}"

        # regex replacement of text
        updated_text = re.sub(pattern, self.replace_values, self.text)

        # Save the page with the updated content
        if self.edit_counter != 0:
            self.page.save(updated_text, summary="DeadBot auto-update")
            print(f"Page '{self.page_name}' updated - {self.edit_counter} new changes")
        else:
            print(f"No changes made to '{self.page_name}'")

    # Either returns the updated value or the original value if nothing has changed
    def replace_values(self, match):
        value_key = match.group(1)
        old_value = match.group(2)

        if value_key in self.master_table:
            new_value = self.master_table[value_key]
            if new_value != old_value:
                self.edit_counter += 1
                return f"{{{{BotValue|key={value_key}|value={new_value}}}}}"
        
        return match.group(0)

if __name__ == '__main__':
    bot = DeadBot()
    bot.run()