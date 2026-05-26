CHANGELOG_RSS_URL = 'https://forums.playdeadlock.com/forums/changelog.10/index.rss'

STEAM_APPID = '1422450'
# count=20 covers the rolling window; maxlength=0 means return full content
STEAM_NEWS_API_URL = f'https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/' f'?appid={STEAM_APPID}&count=20&maxlength=0&format=json'
