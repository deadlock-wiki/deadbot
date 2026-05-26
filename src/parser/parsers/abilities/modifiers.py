import re


_PREFIX_RE = re.compile(r'[A-Z]')
_MODIFIER_VALUES_KEY = 'm_vecAutoRegisterModifierValueFromAbilityPropertyName'


def parse_modifiers(ability: dict) -> dict:
    """Walk an ability and extract a nested modifier hierarchy.

    Any key whose name contains 'modifier' (case-insensitive).
    The output uses the same keys as source but strips the prefixes
    (e.g. m_DebuffModifier -> DebuffModifier,
    m_AutoIntrinsicModifiers -> AutoIntrinsicModifiers).

    From each modifier node, copy:
      - _class -> Class (verbatim, only if a non-empty string)
      - _my_subclass_name -> Subclass (verbatim, only if a non-empty string)
      - m_vecAutoRegisterModifierValueFromAbilityPropertyName ->
        AutoRegisterModifierValueFromAbilityPropertyName (verbatim list of
        property names, only if non-empty).
      - direct int/float children -> key stripped of its lowercase prefix
        (e.g. m_flDuration -> Duration), value verbatim.
      - nested modifier-named children, recursively (same recursion gate).

    Nodes that end up with no fields at all (only empty class etc.) are omitted.
    """
    return _parse_dict_modifiers(ability)


def _strip_prefix(key: str) -> str:
    match = _PREFIX_RE.search(key)
    if match:
        return key[match.start() :]
    return key


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
        out['Class'] = cls
    subclass = node.get('_my_subclass_name')
    if isinstance(subclass, str) and subclass:
        out['Subclass'] = subclass

    auto_register = node.get(_MODIFIER_VALUES_KEY)
    if isinstance(auto_register, list) and auto_register:
        out[_strip_prefix(_MODIFIER_VALUES_KEY)] = auto_register

    for k, v in node.items():
        if k in ('_class', '_my_subclass_name', _MODIFIER_VALUES_KEY):
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[_strip_prefix(k)] = v
            continue
        if 'modifier' in k.lower():
            parsed = _parse_modifier_value(v)
            if parsed is not None:
                out[_strip_prefix(k)] = parsed

    return out or None
