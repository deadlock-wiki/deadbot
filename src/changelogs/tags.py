# Lists and maps regarding changelog tags


class ChangelogTags:
    def __init__(self, default_tag):
        self.default_tag = default_tag
        # Tags to register if they are found in the changelog line
        # match by text
        # avoid putting lowercase tags here, as they are likely to be
        # part of a longer string. Put them in self.tags_match_word instead.
        # See the example for tag_remap for reasoning on shorter/longer strings
        # Lowercase words are more likely to be a prefix/suffix of an uppercase word
        # throwing a false positive match. Such as:
        # "Return Fire changed from...", "urn" would be incorrectly tagged
        # as such, it should only be matched if its a standalone word via match_word
        self.match_text = [
            'Trooper',
            'Base Guardian',
            'Base guardian',
            'base guardian',
            'Guardian',
            'Walker',
            'Patron',
            'Weakened Patron',
            'Weakened patron',
            'Shrine',
            'Mid-Boss',
            'Midboss',
            'MidBoss',
            'Mid Boss',
            'Mid boss',
            'Rejuvenator',
            'Creep',
            'Neutral',
            'Denizen',
            'Golden Statue',
            'Soul',
            'Rope',
            'Zipline',
            'bounce pad',
            'Bounce Pad',
            'Bounce pad',
            'Sapphire',
            'Amber',
            'Veil',
            'Powerup',
            'PowerUp',
            'Crate',
            'Breakable',
        ]
        # match by word
        # add tags here instead of tags_match_text
        # if they are a shorter string, or likely to be part of a longer string
        # or if the lower case also needs to be matched
        self.match_word = [
            'creep',
            'neutral',
            'creeps',
            'neutrals',
            'Rejuv',  # so it doesnt get caught by Rejuvenating Aura
            'Map',
            'urn',
            'Urn',
            'urns',
            'Urns',
            'orb',
            'orbs',
            'Orb',
            'Orbs',
            'soul',
            'souls',
            'rope',
            'ropes',
            'zipline',
            'ziplines',
            'veil',
            'veils',
            'powerup',
            'powerups',
            'crate',
            'crates',
            'breakable',
            'breakables',
        ]

        # texts in this list are not converted to tags
        # useful when they are otherwise added due to being a heading
        self.ignore_list = ['Ranked Mode']

        # remaps tags to a more general tag
        # ensure plural/longer forms are in the list before singular/shorter forms
        # this is so that the plural/longer form is embedded in the text
        # before the singular takes its place
        # i.e. 'Hero Gameplay' -> 'Hero' before 'Hero' -> 'Hero'
        # so that 'Hero Gameplay' -> '{{PageRef|Hero|alt_name=Hero Gameplay}}'
        # instead of '{{PageRef|Hero}} Gameplay'
        self.remap = {
            'Hero Gameplay': 'Hero',
            'Hero Gamepla': 'Hero',
            'Heroes': 'Hero',
            'Abilities': 'Ability',
            'Item Gameplay': 'Item',
            'New Items': 'Item',
            'Items': 'Item',
            'Weapon Items': 'Weapon Item',
            'Spirit Items': 'Spirit Item',
            'Vitality Items': 'Vitality Item',
            'Misc Gameplay': self.default_tag,
            'Misc Gamepla': self.default_tag,
            'General Change': self.default_tag,
            'General': self.default_tag,
            'MidBoss': 'Mid-Boss',
            'Midboss': 'Mid-Boss',
            'Mid Boss': 'Mid-Boss',
            'Mid boss': 'Mid-Boss',
            'Weakened patron': 'Weakened Patron',
            'Rejuv': 'Rejuvenator',
            'creeps': 'Creep',
            'creep': 'Creep',
            'neutrals': 'Denizen',
            'neutral': 'Denizen',
            'Neutral': 'Denizen',
            'urns': 'Urn',
            'Urns': 'Urn',
            'urn': 'Urn',
            'orbs': 'Soul Orb',
            'Orbs': 'Soul Orb',
            'orb': 'Soul Orb',
            'Souls': 'Souls',
            'souls': 'Souls',
            'soul': 'Souls',
            'Soul': 'Souls',
            'Ropes': 'Rope',
            'ropes': 'Rope',
            'rope': 'Rope',
            'ziplines': 'Zipline',
            'Ziplines': 'Zipline',
            'zipline': 'Zipline',
            'Bounce pads': 'Bounce Pad',
            'Bounce Pads': 'Bounce Pad',
            'bounce pad': 'Bounce Pad',
            'Bounce pad': 'Bounce Pad',
            'Base guardian': 'Base Guardian',
            'base guardian': 'Base Guardian',
            'veil': 'Cosmic Veil',
            'veils': 'Cosmic Veil',
            'Veil': 'Cosmic Veil',
            "powerup": "Powerup",
            "PowerUp": "Powerup",
            "powerups": "Powerup",
            "crate": "Crate",
            'crates': 'Crate',
            'breakable': 'Breakable',
            'Breakables': 'Breakable',
            'breakables': 'Breakable',
        }

        # Relations between a child and parent tag where
        # -both are a group tag-. Relationships involving a
        # non-group tag require more explicit parsing within _parse_tags()
        # i.e. Abrams is a parent to Siphon Life, and a child to Hero
        # tags below are after _remap_tag() is called
        # key = child
        # value = parents to assign
        # child, [parents] instead of parent, [children] for easier lookup
        self.parents = {
            'Denizen': ['NPC', 'Creep'],
            'Creep': ['NPC'],
            'Trooper': ['NPC', 'Creep'],
            'Guardian': ['Objective', 'NPC'],
            'Base Guardian': ['Objective', 'NPC'],
            'Walker': ['Objective', 'NPC'],
            'Patron': ['Objective'],
            'Weakened Patron': ['Patron', 'Objective'],
            'Shrine': ['Objective'],
            'Mid-Boss': ['NPC'],
            'Weapon Item': ['Item'],
            'Vitality Item': ['Item'],
            'Spirit Item': ['Item'],
            'Ability': ['Hero'],
            'Soul Orb': ['Souls'],
            'Urn': ['Souls'],
            'Crate': ['Breakable'],
            'Golden Statue': ['Breakable'],
        }
