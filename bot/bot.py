import os
import re
import mwclient

site = mwclient.Site(('https', 'deadlocked.wiki'), path='/')

site.login('DeadBot', os.environ.get('BOT_WIKI_PASSWORD'))

page_name = 'User:Saag/HeroTest'
page = site.pages[page_name]
text = page.text()

new_data =  {
    'test-keyA': 'test-key-A-val',
}


def replace_values(match):
    value_key = match.group(1)
    old_value = match.group(2)
    print('MATCH', value_key in new_data)

    if value_key in new_data:
        new_value = new_data[value_key]
        return f"{{{{BotValue|key={value_key}|value={new_value}}}}}"
    else:
        return match.group(0)

pattern = r"{{BotValue\|key=(.*?)\|value=(.*?)}}"

# regex replacement of text
updated_text = re.sub(pattern, replace_values, text)
print(updated_text)
# # Save the page with the updated content
if text != updated_text:
    page.save(updated_text, summary="Automated update of game stats.")

print(f"Page '{page_name}' updated.")