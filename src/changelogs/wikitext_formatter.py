import re
from typing import Dict, Any, Optional


def format_changelog(
    raw_text: str,
    hero_data: Dict[str, Any],
    item_data: Dict[str, Any],
    ability_data: Dict[str, Any],
    link_targets: Optional[Dict[str, str]] = None,
) -> str:
    """
    Formats a raw changelog string into wikitext by replacing entity names
    with icon templates and converting markdown-style bullet points.

    Args:
        raw_text (str): The raw text of the changelog.
        hero_data (dict): Parsed hero data from hero-data.json.
        item_data (dict): Parsed item data from item-data.json.
        ability_data (dict): Parsed ability data from ability-data.json.
        link_targets (dict): Map of text -> page_name for auto-linking common terms.

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

    # 2. Medium Priority: Curated Wiki Links (from include list)
    # We add these after Icons. Since we use `get` later, existing keys (Icons) won't be overwritten.
    if link_targets:
        for term, page_name in link_targets.items():
            # Skip if this name is already handled by an Icon template (Hero/Ability/Item)
            if term in entity_to_template:
                continue

            # Skip numeric pages to avoid matching parts of numbers
            if term.isdigit():
                continue

            # If term is different from page_name, use pipe to preserve text: [[Page|term]]
            # Otherwise link directly: [[Page]]
            if term != page_name:
                entity_to_template[term] = f'[[{page_name}|{term}]]'
            else:
                entity_to_template[term] = f'[[{page_name}]]'

    # Sort all unique entity names by length in descending order.
    # This is crucial for the regex to match longer names first (e.g., "Smoke Bomb" before "Smoke").
    sorted_names = sorted(list(entity_to_template.keys()), key=len, reverse=True)

    # Convert line-starting hyphens to asterisks for wiki lists.
    wikitext = re.sub(r'^- ', '* ', raw_text, flags=re.MULTILINE)

    if not sorted_names:
        return wikitext

    # Create a single regex to find all entity names. The pattern is built from the
    # length-sorted list, using word boundaries (\b) to prevent partial matches.
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
