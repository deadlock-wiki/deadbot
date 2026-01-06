import re
from typing import Dict, Any, List, Optional

# List of Wiki page titles that should be ignored during auto-linking.
# This prevents words in patch notes from incorrectly linking to pages with the same name
# but different context
IGNORED_PAGES = {
    'Fall',
}


def format_changelog(
    raw_text: str,
    hero_data: Dict[str, Any],
    item_data: Dict[str, Any],
    ability_data: Dict[str, Any],
    wiki_pages: Optional[List[str]] = None,
) -> str:
    """
    Formats a raw changelog string into wikitext by replacing entity names
    with icon templates and converting markdown-style bullet points.

    Args:
        raw_text (str): The raw text of the changelog.
        hero_data (dict): Parsed hero data from hero-data.json.
        item_data (dict): Parsed item data from item-data.json.
        ability_data (dict): Parsed ability data from ability-data.json.
        wiki_pages (list): List of existing page titles on the Wiki.

    Returns:
        str: The formatted wikitext string.
    """
    if not raw_text:
        return ''

    # Create a mapping from entity names to their wikitext templates.
    entity_to_template = {}

    # 1. High Priority: Game Entities (Heroes, Abilities, Items) get Icons
    data_sources = [
        (hero_data, 'HeroIcon'),
        (ability_data, 'AbilityIcon'),
        (item_data, 'ItemIcon'),
    ]

    for data, template_name in data_sources:
        if not data:
            continue
        for entry in data.values():
            name = entry.get('Name')
            # Only add active (not disabled) entities to the template map.
            is_disabled = entry.get('IsDisabled', False)
            if name and not is_disabled:
                entity_to_template[name] = f'{{{{{template_name}|{name}}}}}'

    # 2. Medium Priority: Wiki Page Links
    # We add these after Icons. Since we use `get` later, existing keys (Icons) won't be overwritten.
    if wiki_pages:
        for page in wiki_pages:
            # Skip if this name is already handled by an Icon template
            if page in entity_to_template:
                continue

            # Skip numeric pages (e.g. "7") to avoid matching parts of numbers (e.g. "7.5")
            if page.isdigit():
                continue

            # Skip words that shouldn't be auto-linked
            if page in IGNORED_PAGES:
                continue

            # Case 1: Exact Match
            # If the text is "Urn" and the page is "Urn", we use [[Urn]]
            entity_to_template[page] = f'[[{page}]]'

            # Case 2: Lowercase Match
            # If the text is "urn" and the page is "Urn", we use [[Urn|urn]]
            # This preserves the lowercase look in the changelog sentence
            page_lower = page.lower()
            if page_lower not in entity_to_template:
                entity_to_template[page_lower] = f'[[{page}|{page_lower}]]'

    # Sort all unique entity names by length in descending order.
    # This is crucial for the regex to match longer names first (e.g., "Smoke Bomb" before "Smoke").
    sorted_names = sorted(list(entity_to_template.keys()), key=len, reverse=True)

    # Convert line-starting hyphens to asterisks for wiki lists.
    wikitext = re.sub(r'^- ', '* ', raw_text, flags=re.MULTILINE)

    if not sorted_names:
        return wikitext

    # Create a single regex to find all entity names. The pattern is built from the
    # length-sorted list, using word boundaries (\b) to prevent partial matches.
    # We escape the names to handle special regex characters (like dots or parenthesis).
    pattern_str = r'\b(' + '|'.join(re.escape(name) for name in sorted_names) + r')\b'
    pattern = re.compile(pattern_str)

    # Define a replacer function to look up the template for a matched name.
    def replace_with_template(match: re.Match) -> str:
        matched_name = match.group(0)
        # Fallback to the original name if it's somehow not in the map.
        return entity_to_template.get(matched_name, matched_name)

    # Apply the replacement across the entire text.
    wikitext = pattern.sub(replace_with_template, wikitext)

    return wikitext
