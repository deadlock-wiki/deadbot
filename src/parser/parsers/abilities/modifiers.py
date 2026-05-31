import re


_PREFIX_RE = re.compile(r'[A-Z]')

# Value prefixes shared by class/subclass names and state mask flags.
# Checked longest-first so MODIFIER_STATE_ wins over MODIFIER_.
_MODIFIER_NAME_PREFIXES = ('MODIFIER_STATE_', 'MODIFIER_')


def parse_modifiers(ability: dict) -> dict:
    """Walk an ability and extract a nested modifier hierarchy.

    Any key whose name contains 'modifier' (case-insensitive).
    The output uses the same keys as source but strips the prefixes
    (e.g. m_DebuffModifier -> DebuffModifier,
    m_AutoIntrinsicModifiers -> AutoIntrinsicModifiers).

    From each modifier node, copy:
      - _class -> Class (PascalCased, e.g. modifier_uppercut_debuff ->
        UppercutDebuff, only if a non-empty string)
      - _my_subclass_name -> Subclass (PascalCased, only if a non-empty string)
      - direct int/float children -> key stripped of its lowercase prefix
        (e.g. m_flDuration -> Duration), value verbatim.
      - state mask children (key contains 'StateMask') -> key stripped of its
        prefix (e.g. EnabledStateMask), value split on '|' into a list of
        PascalCased flags (e.g. MODIFIER_STATE_NO_WINDUP -> NoWindup).
      - nested modifier-named children, recursively (same recursion gate).

    Nodes that end up with no fields at all (only empty class etc.) are omitted.
    """
    return _parse_dict_modifiers(ability)


def _strip_prefix(key: str) -> str:
    match = _PREFIX_RE.search(key)
    if match:
        return key[match.start() :]
    return key


def _format_modifier_name(value: str) -> str:
    """Strip a modifier_ / MODIFIER_STATE_ prefix and PascalCase the remainder.

    Each '_'-delimited segment is capitalized (first letter up, rest down) and
    the underscores are dropped, e.g.
      MODIFIER_STATE_NO_WINDUP -> NoWindup
      modifier_uppercut_debuff -> UppercutDebuff
    """
    text = value
    for prefix in _MODIFIER_NAME_PREFIXES:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix) :]
            break
    return ''.join(part.capitalize() for part in text.split('_') if part)


def _parse_state_mask(value: str) -> list:
    """Split a pipe-delimited state mask string into a list of PascalCased flags.

    e.g. "MODIFIER_STATE_DISARMED | MODIFIER_STATE_NO_WINDUP" -> ['Disarmed', 'NoWindup'].
    """
    return [_format_modifier_name(token.strip()) for token in value.split('|') if token.strip()]


def _parse_dict_modifiers(node: dict) -> dict:
    out = {}
    for k, v in node.items():
        if 'modifier' not in k.lower():
            continue
        parsed = _parse_modifier_value(v)
        if parsed is not None:
            out[_strip_prefix(k)] = parsed
    return out


def _parse_modifier_value(value):
    if isinstance(value, dict):
        return _parse_modifier_node(value)
    if isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, dict):
                continue
            parsed = _parse_modifier_node(item)
            if parsed is not None:
                items.append(parsed)
        return items if items else None
    return None


def _parse_modifier_node(node: dict) -> dict | None:
    out = {}

    cls = node.get('_class')
    if isinstance(cls, str) and cls:
        out['Class'] = _format_modifier_name(cls)
    subclass = node.get('_my_subclass_name')
    if isinstance(subclass, str) and subclass:
        out['Subclass'] = _format_modifier_name(subclass)

    for k, v in node.items():
        if k in ('_class', '_my_subclass_name'):
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[_strip_prefix(k)] = v
            continue
        if 'statemask' in k.lower() and isinstance(v, str) and v:
            out[_strip_prefix(k)] = _parse_state_mask(v)
            continue
        if 'modifier' in k.lower():
            # Unlike state masks, a non-empty node can still parse to None when
            # all of its children are filtered out, so the guard is required.
            parsed = _parse_modifier_value(v)
            if parsed is not None:
                out[_strip_prefix(k)] = parsed

    return out or None
