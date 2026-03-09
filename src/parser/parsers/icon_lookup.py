import utils.json_utils as json_utils


class IconLookupParser:
    """
    Builds a pre-indexed icon lookup table from already-parsed hero, ability, and item data.
    The keys are lowercase entity names, allowing Module:Icon on the wiki to do a direct
    O(1) lookup via mw.loadJsonData instead of iterating all three datasets on every page render.
    """

    # Heroes that don't have images uploaded yet
    MISSING_IMAGE_OVERRIDES = {
        'boho': 'Module-Icon missing.png',
        'druid': 'Module-Icon missing.png',
        'fortuna': 'Module-Icon missing.png',
        'graf': 'Module-Icon missing.png',
        'gunslinger': 'Module-Icon missing.png',
        'skyrunner': 'Module-Icon missing.png',
        'swan': 'Module-Icon missing.png',
        'thumper': 'Module-Icon missing.png',
    }

    # Items that link to disambiguation pages
    LINK_OVERRIDES = {
        'Bullet Lifesteal': 'Bullet Lifesteal (item)',
        'Spirit Lifesteal': 'Spirit Lifesteal (item)',
    }

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
            image = self.MISSING_IMAGE_OVERRIDES.get(lower_name, name + '.png')

            lookup[lower_name] = {
                'name': name,
                'key': hero_key,
                'link': name,
                'image': image,
                'type': 'hero',
            }

            # Map abilities to their parent hero for linking
            for _, ability in (hero.get('BoundAbilities') or {}).items():
                if ability.get('Key'):
                    ability_to_hero[ability['Key']] = name

        # Process Abilities
        for ability_key, ability in self.parsed_abilities.items():
            if not isinstance(ability, dict) or not ability.get('Name'):
                continue
            if ability.get('IsDisabled'):
                continue

            name = ability['Name']
            lower_name = name.lower()
            parent_hero = ability_to_hero.get(ability_key)
            link = parent_hero or name

            existing = lookup.get(lower_name)

            if existing is None:
                lookup[lower_name] = {
                    'name': name,
                    'key': ability_key,
                    'link': link,
                    'image': name + '.png',
                    'type': 'ability',
                    'class': 'theme',
                }
            elif existing['type'] == 'ability':
                # Prefer the entry that is linked to a hero over an orphan
                existing_has_parent = existing['link'] != existing['name']
                if not existing_has_parent and parent_hero:
                    lookup[lower_name] = {
                        'name': name,
                        'key': ability_key,
                        'link': link,
                        'image': name + '.png',
                        'type': 'ability',
                        'class': 'theme',
                    }

        # Process Items
        for item_key, item in self.parsed_items.items():
            if not isinstance(item, dict) or not item.get('Name'):
                continue
            if item.get('IsDisabled'):
                continue

            name = item['Name']
            lower_name = name.lower()
            link = self.LINK_OVERRIDES.get(name, name)

            lookup[lower_name] = {
                'name': name,
                'key': item_key,
                'link': link,
                'image': name + '.png',
                'type': 'item',
            }

        return json_utils.sort_dict(lookup)
