import re
from typing import Dict, Any

def format_changelog(
    raw_text: str,
    hero_data: Dict[str, Any],
    item_data: Dict[str, Any],
    ability_data: Dict[str, Any],
) -> str:
    """
    Formats a raw changelog string into wikitext by replacing entity names
    with icon templates and converting markdown-style bullet points.

    Args:
        raw_text (str): The raw text of the changelog.
        hero_data (dict): Parsed hero data from hero-data.json.
        item_data (dict): Parsed item data from item-data.json.
        ability_data (dict): Parsed ability data from ability-data.json.

    Returns:
        str: The formatted wikitext string.
    """
    if not raw_text:
        return ""

    # 1. Create a mapping from entity names to their wikitext templates.
    entity_to_template = {}
    data_sources = [
        (hero_data, "HeroIcon"),
        (item_data, "ItemIcon"),
        (ability_data, "AbilityIcon"),
    ]

    for data, template_name in data_sources:
        if not data:
            continue
        for entry in data.values():
            name = entry.get("Name")
            if name:  # Ensure name is not None or empty
                entity_to_template[name] = f"{{{{{template_name}|{name}}}}}"

    # 2. Sort all unique entity names by length in descending order.
    # This is crucial for the regex to match longer names first (e.g., "Smoke Bomb" before "Smoke").
    sorted_names = sorted(list(entity_to_template.keys()), key=len, reverse=True)

    # 3. Convert line-starting hyphens to asterisks for wiki lists.
    # This is done before entity replacement for simplicity.
    wikitext = re.sub(r"^- ", "* ", raw_text, flags=re.MULTILINE)

    # If there are no entities to replace, we can return early.
    if not sorted_names:
        return wikitext

    # 4. Create a single regex to find all entity names.
    # The pattern is built from the length-sorted list of names.
    # The \b ensures we match whole words only.
    pattern_str = r'\b(' + '|'.join(re.escape(name) for name in sorted_names) + r')\b'
    pattern = re.compile(pattern_str)

    # 5. Define a replacer function to look up the template for a matched name.
    def replace_with_template(match: re.Match) -> str:
        matched_name = match.group(0)
        # Fallback to the original name if it's somehow not in the map (should not happen)
        return entity_to_template.get(matched_name, matched_name)

    # 6. Apply the replacement across the entire text.
    wikitext = pattern.sub(replace_with_template, wikitext)

    return wikitext