import utils.json_utils as json_utils


class ResourceLookupParser:
    """
    Builds a pre-indexed name -> resource lookup table from already-parsed hero,
    ability, and item data. Keys are lowercase entity names, allowing wiki modules
    to do a direct O(1) lookup via mw.loadJsonData instead of iterating all three
    datasets on every page render.

    Wiki-specific logic (image paths, links, CSS classes) is intentionally left
    to the wiki side for easier maintenance. Only non-inferable fields are included.
    """

    def __init__(self, parsed_heroes, parsed_abilities, parsed_items):
        self.parsed_heroes = parsed_heroes
        self.parsed_abilities = parsed_abilities
        self.parsed_items = parsed_items

    def run(self):
        lookup = {}
        ability_to_hero = {}

        # Process Heroes
        for hero_key, hero in self.parsed_heroes.items():
            if not isinstance(hero, dict) or not hero.get('Name'):
                continue

            name = hero['Name']
            lower_name = name.lower()

            lookup[lower_name] = {
                'name': name,
                'key': hero_key,
                'type': 'hero',
            }

            # Map ability keys to their parent hero for linking
            for _, ability in (hero.get('BoundAbilities') or {}).items():
                if ability.get('Key'):
                    ability_to_hero[ability['Key']] = {
                        'hero_name': name,
                        'hero_key': hero_key,
                    }

        # Process Abilities
        for ability_key, ability in self.parsed_abilities.items():
            if not isinstance(ability, dict) or not ability.get('Name'):
                continue
            if ability.get('IsDisabled'):
                continue

            name = ability['Name']
            lower_name = name.lower()
            parent = ability_to_hero.get(ability_key)
            hero_name = parent['hero_name'] if parent else None
            hero_key = parent['hero_key'] if parent else None

            # Skip NPC abilities - lookup is only for hero abilities, heroes, and items
            if hero_name is None:
                continue

            existing = lookup.get(lower_name)
            if existing is not None and existing['type'] == 'ability':
                # Prefer the entry that is linked to a hero over an orphan
                if existing.get('hero_name') is not None:
                    continue

            lookup[lower_name] = {
                'name': name,
                'key': ability_key,
                'hero_name': hero_name,
                'hero_key': hero_key,
                'type': 'ability',
            }

        # Process Items
        for item_key, item in self.parsed_items.items():
            if not isinstance(item, dict) or not item.get('Name'):
                continue
            if item.get('IsDisabled'):
                continue

            name = item['Name']
            lower_name = name.lower()

            lookup[lower_name] = {
                'name': name,
                'key': item_key,
                'type': 'item',
            }

        return json_utils.sort_dict(lookup)
