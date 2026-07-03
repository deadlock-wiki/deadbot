import re
from typing import Dict, Any, Optional, List, Tuple

GAME_MODE_SECTIONS = ['Street Brawl']

GENERIC_HEADERS = {
    'general',
    'general changes',
    'items',
    'items changes',
    'item gameplay',
    'item gameplay changes',
    'weapon items',
    'vitality items',
    'spirit items',
    'new items',
    'heroes',
    'hero changes',
    'hero gameplay',
    'hero gameplay changes',
    'misc gameplay',
    'misc gameplay changes',
    'gameplay changes',
    'abilities',
    'ability changes',
}


def format_changelog(
    raw_text: str,
    hero_data: Dict[str, Any],
    item_data: Dict[str, Any],
    ability_data: Dict[str, Any],
    link_targets: Optional[Dict[str, list]] = None,
) -> str:
    if not raw_text:
        return ''

    heroes = [v.get('Name') for v in hero_data.values() if v.get('Name') and not v.get('IsDisabled')]
    items = [v.get('Name') for v in item_data.values() if v.get('Name') and not v.get('IsDisabled')]
    abilities = [v.get('Name') for v in ability_data.values() if v.get('Name') and not v.get('IsDisabled')]

    parts = re.split(r'(=== Patch \d+ ===)', raw_text)

    patch_blocks = []
    if parts[0].strip():
        patch_blocks.append(('Patch 1', parts[0]))

    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            header = parts[i].strip('= ').strip()
            patch_blocks.append((header, parts[i + 1]))

    out = []
    is_first_patch = True

    for patch_name, patch_text in patch_blocks:
        if not is_first_patch or patch_name != 'Patch 1':
            out.append(f'=== {patch_name} ===')
            out.append('')
        is_first_patch = False

        entries = _parse_entries(patch_text)
        out.extend(_build_output(entries, heroes, items, abilities, link_targets))
        out.append('')

    return '\n'.join(out).strip() + '\n'


def _parse_entries(raw_text: str) -> List[Tuple[str, str]]:
    entries = []
    current = None

    for line in raw_text.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current is not None:
                entries.append(('entry', current))
                current = None
            continue

        if stripped.startswith('[') and stripped.endswith(']'):
            if current is not None:
                entries.append(('entry', current))
                current = None

            header_text = stripped[1:-1].strip()
            if header_text.lower() not in GENERIC_HEADERS:
                entries.append(('header', header_text))
            continue

        if stripped.startswith('-') or stripped.startswith('*'):
            if current is not None:
                entries.append(('entry', current))
            current = stripped.lstrip('-* ').strip()
        elif current is not None:
            current += ' ' + stripped

    if current is not None:
        entries.append(('entry', current))

    cleaned_entries = []
    for kind, text in entries:
        if kind == 'entry':
            cleaned_entries.append((kind, re.sub(r'\s+', ' ', text).strip()))
        else:
            cleaned_entries.append((kind, text))
    return cleaned_entries


def _classify_entry(entry: str, heroes: list, items: list, game_modes: list) -> Tuple[str, Optional[str], str]:
    idx = entry.find(':')
    if idx != -1:
        prefix = entry[:idx].strip()
        rest = entry[idx + 1 :].strip()

        if prefix in game_modes:
            return ('mode', prefix, rest)
        if prefix in heroes:
            return ('hero', prefix, rest)
        if prefix in items:
            return ('item', prefix, rest)

    return ('general', None, entry)


def _find_and_remove_ability(text: str, abilities: list) -> Tuple[Optional[str], str]:
    best_match = {'ability': None, 'index': float('inf'), 'length': 0}

    for ability in sorted(abilities, key=len, reverse=True):
        pattern = re.compile(r'(?<!\w)' + re.escape(ability) + r'(?!\w)', re.IGNORECASE)
        match = pattern.search(text)
        if match:
            if match.start() < best_match['index'] or (match.start() == best_match['index'] and len(match.group(0)) > best_match['length']):
                best_match = {'ability': ability, 'index': match.start(), 'length': len(match.group(0))}

    if best_match['ability']:
        start, end = best_match['index'], best_match['index'] + best_match['length']
        cleaned_text = text[:start] + text[end:]
        cleaned_text = re.sub(r'^[\s:–—-]+', '', cleaned_text).strip()
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return best_match['ability'], cleaned_text

    return None, text


def _format_body(
    text: str,
    heroes: list,
    items: list,
    abilities: list,
    excluded_ability: Optional[str] = None,
    link_targets: Optional[dict] = None,
) -> str:
    protected_tokens = []

    def protect(value: str) -> str:
        token = f'\x00{len(protected_tokens)}\x00'
        protected_tokens.append(value)
        return token

    text = re.sub(r'\{\{(?:Ability|Hero|Item)Icon\|[^{}]+\}\}', lambda m: protect(m.group(0)), text)

    replacements = {}

    abilities_to_wrap = [a for a in abilities if a != excluded_ability]
    for name in abilities_to_wrap:
        replacements[name] = f'{{{{AbilityIcon|{name}}}}}'
    for name in items:
        replacements[name] = f'{{{{ItemIcon|{name}}}}}'
    for name in heroes:
        replacements[name] = f'{{{{HeroIcon|{name}}}}}'

    if link_targets:
        for page_name, aliases in link_targets.items():
            for alias in aliases:
                if alias.isdigit() or alias in replacements:
                    continue
                if alias != page_name:
                    replacements[alias] = f'[[{page_name}|{alias}]]'
                else:
                    replacements[alias] = f'[[{page_name}]]'

    sorted_terms = sorted(replacements.keys(), key=len, reverse=True)

    for term in sorted_terms:
        pattern = re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)')
        text = pattern.sub(lambda m: protect(replacements[term]), text)

    for i, original in enumerate(protected_tokens):
        text = text.replace(f'\x00{i}\x00', original)

    return text


def _build_output(entries: list, heroes: list, items: list, abilities: list, link_targets: Optional[dict]) -> List[str]:
    general = []
    modes = {}
    mode_order = []
    item_sections = {}
    item_order = []
    hero_sections = {}
    hero_order = []

    for kind, entry in entries:
        if kind == 'header':
            general.append(f'== {entry} ==')
            continue

        kind, name, body = _classify_entry(entry, heroes, items, GAME_MODE_SECTIONS)

        if kind == 'general':
            general.append('* ' + _format_body(body, heroes, items, abilities, link_targets=link_targets))

        elif kind == 'mode':
            if name not in modes:
                modes[name] = []
                mode_order.append(name)
            modes[name].append('* ' + _format_body(body, heroes, items, abilities, link_targets=link_targets))

        elif kind == 'item':
            if name not in item_sections:
                item_sections[name] = []
                item_order.append(name)
            item_sections[name].append('* {{Change|}} ' + _format_body(body, heroes, items, abilities, link_targets=link_targets))

        elif kind == 'hero':
            if name not in hero_sections:
                hero_sections[name] = {'general': [], 'abilities': {}, 'ability_order': []}
                hero_order.append(name)

            section = hero_sections[name]
            ability_name, cleaned_body = _find_and_remove_ability(body, abilities)

            if ability_name and cleaned_body:
                if ability_name not in section['abilities']:
                    section['abilities'][ability_name] = []
                    section['ability_order'].append(ability_name)
                cleaned_body = cleaned_body[0].upper() + cleaned_body[1:] if cleaned_body else cleaned_body
                section['abilities'][ability_name].append(
                    '* {{Change|}} ' + _format_body(cleaned_body, heroes, items, abilities, excluded_ability=ability_name, link_targets=link_targets)
                )
            else:
                section['general'].append('* {{Change|}} ' + _format_body(body, heroes, items, abilities, link_targets=link_targets))

    out = []

    for entry in general:
        out.append(entry)

    for mode in mode_order:
        out.append('')
        out.append(f'== [[{mode}]] ==')
        for body in modes[mode]:
            out.append(body)

    if item_order:
        out.append('')
        out.append('= Items =')
        for item in item_order:
            out.append(f'== {{{{ItemIcon|{item}}}}} ==')
            for body in item_sections[item]:
                out.append(body)

    if hero_order:
        out.append('')
        out.append('= Heroes =')
        for hero in hero_order:
            out.append(f'== {{{{HeroIcon|{hero}}}}} ==')
            section = hero_sections[hero]

            for body in section['general']:
                out.append(body)

            for ability in section['ability_order']:
                out.append(f'==== {{{{AbilityIcon|{ability}}}}} ====')
                for body in section['abilities'][ability]:
                    out.append(body)

    return out
