# Maps page name in "Data:" namespace on the wiki to
# the file path in $OUTPUT_DIR
DATA_PAGE_FILE_MAP = {
    'AbilityCards.json': 'json/ability-cards.json',
    'AbilityData.json': 'json/ability-data.json',
    'AttributeData.json': 'json/attribute-data.json',
    'HeroData.json': 'json/hero-data.json',
    'ItemData.json': 'json/item-data.json',
    'Lang en.json': 'localizations/english.json',
    'Lang es.json': 'localizations/spanish.json',
    'Lang ru.json': 'localizations/russian.json',
    'Lang tr.json': 'localizations/turkish.json',
    'Lang zh-hans.json': 'localizations/schinese.json',
    'Lang zh-hant.json': 'localizations/tchinese.json',
    'SoulUnlockData.json': 'json/soul-unlock-data.json',
    'StatInfoboxOrder.json': 'json/stat-infobox-order.json',
}

# Ignore these pages as they are not automated
IGNORE_PAGES = [
    'Dictionary',
    'Dictionary/sources',
    'Dictionary.json/sources',
    'LangCodes.json',
]
