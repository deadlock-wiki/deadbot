# Maps page name in "Data:" namespace on the wiki to
# the file path in $OUTPUT_DIR
DATA_PAGE_FILE_MAP = {
    'json/ability-cards.json': 'AbilityCards.json',
    'json/ability-data.json': 'AbilityData.json',
    'json/attribute-data.json': 'AttributeData.json',
    'json/hero-data.json': 'HeroData.json',
    'json/item-data.json': 'ItemData.json',
    'json/soul-unlock-data.json': 'SoulUnlockData.json',
    'json/stat-infobox-order.json': 'StatInfoboxOrder.json',
    'localizations/english.json': 'Lang en.json',
    'localizations/spanish.json': 'Lang es.json',
    'localizations/russian.json': 'Lang ru.json',
    'localizations/turkish.json': 'Lang tr.json',
    'localizations/schinese.json': 'Lang zh-hans.json',
    'localizations/tchinese.json': 'Lang zh-hant.json',
}

CHANGELOGS_PAGE_DIR = 'changelogs/versions/'
CHANGELOGS_PAGE_DEST = 'Changelog <version>.json'

# Ignore these pages as they are not automated
IGNORE_PAGES = [
    'Dictionary',
    'Dictionary/sources',
    'Dictionary.json/sources',
    'LangCodes.json',
]
