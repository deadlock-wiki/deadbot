import re
from typing import Any, Dict, List, Optional, Tuple


# Game mode names that should produce their own section rather than being classified as items or heroes.
GAME_MODE_SECTIONS = ['Street Brawl']

# fetch_changelogs.py inserts "=== Patch N ===" headers when merging same-day Steam posts.
# This regex segments on those headers so each patch block is grouped independently.
_PATCH_HEADER_RE = re.compile(r'^==\s*Patch\s+\d+\s*==$', re.MULTILINE)


def format_changelog(
    raw_text: str,
    hero_data: Dict[str, Any],
    item_data: Dict[str, Any],
    ability_data: Dict[str, Any],
    link_targets: Optional[Dict[str, list]] = None,
) -> str:
    """
    Formats a raw changelog string into structured wikitext.
    Categorizes entries into Game Modes, Items, and Heroes/Abilities,
    and replaces entity names with icon templates.

    Args:
        raw_text: The raw text of the changelog.
        hero_data: Parsed hero data from hero-data.json.
        item_data: Parsed item data from item-data.json.
        ability_data: Parsed ability data from ability-data.json.
        link_targets: Map of page_name -> list of aliases for auto-linking common terms.

    Returns:
        The formatted wikitext string.
    """
    if not raw_text:
        return ''

    heroes, items, abilities = _collect_names(hero_data, item_data, ability_data)

    parts = _PATCH_HEADER_RE.split(raw_text)
    headers = _PATCH_HEADER_RE.findall(raw_text)
    segments = [(None, parts[0])] + list(zip(headers, parts[1:]))

    output_blocks = []
    for header, body_text in segments:
        entries = _parse_entries(body_text)
        section_text = _format_entries(entries, heroes, items, abilities, link_targets)

        if header:
            output_blocks.append(header.strip())
        if section_text:
            output_blocks.append(section_text)

    if not output_blocks:
        return ''

    return '\n\n'.join(output_blocks).strip() + '\n'


def _format_entries(
    entries: List[str],
    heroes: List[str],
    items: List[str],
    abilities: List[str],
    link_targets: Optional[Dict[str, list]],
) -> str:
    """
    Parses flat bullet-point entries and categorizes them into a structured hierarchy.
    Builds nested dictionaries for Game Modes, Items, and Heroes (with sub-sections for abilities),
    then passes the formatted text to _build_output to generate the final wikitext layout.
    """
    general: List[str] = []
    modes: Dict[str, List[str]] = {}
    mode_order: List[str] = []
    item_sections: Dict[str, List[str]] = {}
    item_order: List[str] = []
    hero_sections: Dict[str, Dict[str, Any]] = {}
    hero_order: List[str] = []

    for entry in entries:
        kind, name, body = _classify(entry, heroes, items, GAME_MODE_SECTIONS)

        if kind == 'general':
            general.append(_format_body(body, heroes, abilities, items, link_targets))

        elif kind == 'mode':
            if name not in modes:
                modes[name] = []
                mode_order.append(name)
            modes[name].append(_format_body(body, heroes, abilities, items, link_targets))

        elif kind == 'item':
            if name not in item_sections:
                item_sections[name] = []
                item_order.append(name)
            formatted = _format_body(body, heroes, abilities, items, link_targets)
            item_sections[name].append(f'* {{{{Change|}}}} {formatted}')

        elif kind == 'hero':
            if name not in hero_sections:
                hero_sections[name] = {'general': [], 'ability_sections': {}, 'ability_order': []}
                hero_order.append(name)

            section = hero_sections[name]
            mention = _find_ability_mention(body, abilities)

            if mention:
                start, end, ability = mention
                cleaned = _remove_ability_mention(body, start, end)
            else:
                cleaned, ability = None, None

            if mention and cleaned:
                if ability not in section['ability_sections']:
                    section['ability_sections'][ability] = []
                    section['ability_order'].append(ability)

                formatted = _format_body(_capitalize_first(cleaned), heroes, abilities, items, link_targets, excluded_ability=ability)
                section['ability_sections'][ability].append(f'* {{{{Change|}}}} {formatted}')
            else:
                formatted = _format_body(body, heroes, abilities, items, link_targets)
                section['general'].append(f'* {{{{Change|}}}} {formatted}')

    return _build_output(general, modes, mode_order, item_sections, item_order, hero_sections, hero_order)


def _collect_names(hero_data, item_data, ability_data) -> Tuple[List[str], List[str], List[str]]:
    return _active_names(hero_data), _active_names(item_data), _active_names(ability_data)


def _active_names(data: Dict[str, Any]) -> List[str]:
    if not data:
        return []
    return [entry['Name'] for entry in data.values() if entry.get('Name') and not entry.get('IsDisabled', False)]


def _parse_entries(raw_text: str) -> List[str]:
    """
    Splits raw text into individual bullet-point entries.
    Lines starting with ``-`` start a new entry; subsequent indented lines without a
    leading ``-`` are treated as continuation text of the current entry.
    """
    entries: List[str] = []
    current: Optional[str] = None

    for line in raw_text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('-'):
            if current is not None:
                entries.append(current)
            current = stripped[1:].strip()
        elif current is not None:
            current += ' ' + stripped

    if current is not None:
        entries.append(current)

    return [re.sub(r'\s+', ' ', e).strip() for e in entries if e.strip()]


def _match_hero_prefix(raw_prefix: str, heroes: List[str]) -> Optional[str]:
    """
    Returns the canonical hero name matching *raw_prefix*, or ``None``.

    Patch notes sometimes refer to a hero by its sort name (e.g. ``Doorman``) while the
    game data stores the display name (e.g. ``The Doorman``).  This function tries an
    exact match first, then falls back to stripping a leading ``The `` prefix.
    """
    if raw_prefix in heroes:
        return raw_prefix
    for hero in heroes:
        if hero.startswith('The ') and raw_prefix == hero[4:]:
            return hero
    return None


def _classify(entry: str, heroes: List[str], items: List[str], game_modes: List[str]) -> Tuple[str, Optional[str], str]:
    """
    Determines whether an entry belongs to a game mode, hero, item, or is general.

    The first ``:`` in the entry separates the prefix (entity name) from the body.
    Priority order: mode > hero > item > general.
    """
    idx = entry.find(':')
    if idx != -1:
        raw_prefix = entry[:idx].strip()
        rest = entry[idx + 1 :].strip()

        if raw_prefix in game_modes:
            return 'mode', raw_prefix, rest

        matched_hero = _match_hero_prefix(raw_prefix, heroes)
        if matched_hero:
            return 'hero', matched_hero, rest

        if raw_prefix in items:
            return 'item', raw_prefix, rest

    return 'general', None, entry


def _format_body(
    text: str,
    heroes: List[str],
    abilities: List[str],
    items: List[str],
    link_targets: Optional[Dict[str, list]],
    excluded_ability: Optional[str] = None,
) -> str:
    # Tokenization strategy: replace matched entities with temporary null-byte tokens.
    # This prevents nested replacements (e.g. matching "Melee" inside an already-generated
    # "{{Heavy Melee}}" icon template). Tokens are restored at the end.
    protected: List[str] = []

    def protect(value: str) -> str:
        token = f'\x00{len(protected)}\x00'
        protected.append(value)
        return token

    def wrap(terms: List[str], template_name: str) -> None:
        nonlocal text
        # Process longer names first so "Smoke Bomb" is matched before "Smoke".
        for term in sorted(dict.fromkeys(terms), key=len, reverse=True):
            if not term:
                continue
            pattern = re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)')
            replacement = '{{' + template_name + '|' + term + '}}'
            text = pattern.sub(lambda m, r=replacement: protect(r), text)

    # Apply icon templates in priority order: ability > item > hero.
    # Exclude the ability that was already used as a sub-heading to avoid redundancy.
    ability_terms = [a for a in abilities if a != excluded_ability]
    wrap(ability_terms, 'AbilityIcon')
    wrap(items, 'ItemIcon')
    wrap(heroes, 'HeroIcon')

    # Apply link_targets auto-links for terms not already claimed by icon templates.
    if link_targets:
        claimed = set(ability_terms) | set(items) | set(heroes)
        for page_name, aliases in link_targets.items():
            for term in aliases:
                if term in claimed or term.isdigit():
                    continue
                pattern = re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)')
                replacement = f'[[{page_name}]]' if term == page_name else f'[[{page_name}|{term}]]'
                text = pattern.sub(lambda m, r=replacement: protect(r), text)

    for i, value in enumerate(protected):
        text = text.replace(f'\x00{i}\x00', value)

    return text


def _find_ability_mention(text: str, abilities: List[str]) -> Optional[Tuple[int, int, str]]:
    """
    Finds the leftmost ability name in *text*.

    Returns ``(start, end, ability_name)`` or ``None``.  When multiple abilities start at
    the same position the longer name wins (e.g. ``Heavy Barrage`` over ``Barrage``).
    """
    best: Optional[Tuple[int, int, str]] = None
    for ability in sorted(dict.fromkeys(abilities), key=len, reverse=True):
        pattern = re.compile(r'(?<!\w)' + re.escape(ability) + r'(?!\w)')
        match = pattern.search(text)
        if not match:
            continue
        candidate = (match.start(), match.end(), ability)
        if best is None or candidate[0] < best[0] or (candidate[0] == best[0] and (candidate[1] - candidate[0]) > (best[1] - best[0])):
            best = candidate
    return best


def _remove_ability_mention(text: str, start: int, end: int) -> str:
    """Strips the ability name from *text* and cleans up surrounding punctuation."""
    remaining = text[:start] + text[end:]
    remaining = re.sub(r'^[\s:\-\u2013\u2014]+', '', remaining)
    return re.sub(r'\s+', ' ', remaining).strip()


def _capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _build_output(general, modes, mode_order, item_sections, item_order, hero_sections, hero_order) -> str:
    """
    Assembles the final wikitext string from the categorized entry lists.

    Output section order:
        1. General entries (no prefix match)
        2. Game mode sections (``== [[Mode]] ==``)
        3. ``== Items ==`` with per-item sub-headings
        4. ``== Heroes ==`` with per-hero and per-ability sub-headings
    """
    lines: List[str] = []

    for entry in general:
        lines.append(f'* {entry}')

    for mode in mode_order:
        lines.append('')
        lines.append(f'== [[{mode}]] ==')
        for body in modes[mode]:
            lines.append(f'* {body}')

    if item_order:
        lines.append('')
        lines.append('== Items ==')
        for item in item_order:
            lines.append(f'=== {{{{ItemIcon|{item}}}}} ===')
            lines.extend(item_sections[item])

    if hero_order:
        lines.append('')
        lines.append('== Heroes ==')
        for hero in hero_order:
            section = hero_sections[hero]
            lines.append(f'=== {{{{HeroIcon|{hero}}}}} ===')
            lines.extend(section['general'])
            for ability in section['ability_order']:
                lines.append(f'==== {{{{AbilityIcon|{ability}}}}} ====')
                lines.extend(section['ability_sections'][ability])

    return '\n'.join(lines).strip()
