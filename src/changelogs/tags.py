import utils.json_utils as json_utils


class ChangelogTags:
    """
    Lists and maps regarding changelog tags
    """

    def __init__(self, default_tag, OUTPUT_CHANGELOGS):
        self.default_tag = default_tag
        self.OUTPUT_CHANGELOGS = OUTPUT_CHANGELOGS
        # Tags to register if they are found in the changelog line
        # match by text
        # avoid putting tags that are lowercase/short/1 word here.
        # Put them in match_word instead.
        # Such tags are likely to be a prefix/suffix of another word
        # throwing a false positive match. Such as:
        # "Return Fire changed from...", "urn" would be incorrectly tagged
        # as such, it should only be matched if its a standalone word via match_word
        # order also matters, see the example in self.remap
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
            'Souls',
            'Rope',
            'Zipline',
            'bounce pad',
            'Bounce Pad',
            'Bounce pad',
            'Sapphire Hand',
            'Sapphire',
            'Amber Hand',
            'Amber',
            'Veil',
            'Powerup',
            'PowerUp',
            'Power Up',
            'Power up',
            'Power ups',
            'power up',
            'power ups',
            'PowerUps',
            'Crate',
            'Breakable',
            'Sandbox',
            'Shop',
            'Minimap',
            'Parry',
            'Light Melee',
            'Heavy Melee',
            'Light melee',
            'Heavy melee',
            'light melee',
            'heavy melee',
            'Melee',
            'Objective',
            'Vault',
            "Sinner's Sacrifice",
            'Sinners Sacrifice',
            "Sinners' Sacrifice",
            'Sinner Sacrifice',
            "Sinner's sacrifice",
            'Sinners sacrifice',
            "Sinners' sacrifice",
            'Sinner sacrifice',
            "sinner's sacrifice",
            'sinners sacrifice',
            "sinners' sacrifice",
            'sinner sacrifice',
            'Flex Slot',
            'flex slot',
            'Flex slot',
            'flex slots',
            'Flex',
            'Greenwich',
            'York Avenue',
            'Broadway',
            'Park Avenue',
            'Department Store',
            'Arcade',
            'Fish Market',
            'Basement',
            'Bridge',
            'Hotel',
            'Pharmacy',
            'Penn Station',
            'Grand Central',
        ]
        # match by word
        # if they are a shorter string, or likely to be part of a longer string
        # or if the lower case also needs to be matched
        # spaces are not allowed in this list, it will need to go in the above list
        self.match_word = [
            'creep',
            'neutral',
            'creeps',
            'neutrals',
            'Rejuv',  # so it doesnt get caught by Rejuvenating Aura
            'minimap',
            'minimaps',
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
            'sandbox',
            'shop',
            'shops',
            'parry',
            'parried',
            'melee',
            'melees',
            'Idol',
            'idol',
            'Pause',
            'vault',
            'vaults',
            'Gun',
            'gun',
            'guns',
            'Guns',
            'Pit',
            'pit',
            'Pits',
            'pits',
        ]

        # texts in this list are not converted to tags
        # useful when they are otherwise added due to being a heading
        self.ignore_list = ['Ranked Mode', 'Rem']

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
            'urns': 'Soul Urn',
            'Urns': 'Soul Urn',
            'urn': 'Soul Urn',
            'Urn': 'Soul Urn',
            'Idol': 'Soul Urn',
            'idol': 'Soul Urn',
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
            'Sapphire': 'Sapphire Hand',
            'Amber': 'Amber Hand',
            'veil': 'Cosmic Veil',
            'veils': 'Cosmic Veil',
            'Veil': 'Cosmic Veil',
            'powerup': 'PowerUp',
            'PowerUp': 'PowerUp',
            'powerups': 'PowerUp',
            'Power Up': 'PowerUp',
            'Power up': 'PowerUp',
            'Power ups': 'PowerUp',
            'PowerUps': 'PowerUp',
            'power up': 'PowerUp',
            'power ups': 'PowerUp',
            'crate': 'Crate',
            'crates': 'Crate',
            'breakable': 'Breakable',
            'Breakables': 'Breakable',
            'breakables': 'Breakable',
            'sandbox': 'Sandbox',
            'shops': 'Shop',
            'shop': 'Shop',
            'minimap': 'Map',
            'minimaps': 'Map',
            'Minimap': 'Map',
            'parry': 'Parry',
            'parried': 'Parry',
            'light melee': 'Light Melee',
            'heavy melee': 'Heavy Melee',
            'Light melee': 'Light Melee',
            'Heavy melee': 'Heavy Melee',
            'melee': 'Melee',
            'melees': 'Melee',
            'pause': 'Pause',
            'pauses': 'Pause',
            'paused': 'Pause',
            'vaults': "Sinner's Sacrifice",
            'vault': "Sinner's Sacrifice",
            'Vault': "Sinner's Sacrifice",
            "Sinner's sacrifice": "Sinner's Sacrifice",
            'Sinners sacrifice': "Sinner's Sacrifice",
            "Sinners' sacrifice": "Sinner's Sacrifice",
            'Sinner sacrifice': "Sinner's Sacrifice",
            "sinner's sacrifice": "Sinner's Sacrifice",
            'sinners sacrifice': "Sinner's Sacrifice",
            "sinners' sacrifice": "Sinner's Sacrifice",
            'sinner sacrifice': "Sinner's Sacrifice",
            'flex slot': 'Flex Slot',
            'Flex slot': 'Flex Slot',
            'flex slots': 'Flex Slot',
            'Flex': 'Flex Slot',
            'guns': 'Weapon',
            'gun': 'Weapon',
            'Guns': 'Weapon',
            'Gun': 'Weapon',
            'Pits': 'Pit',
            'pit': 'Pit',
            'pits': 'Pit',
        }

        # Relations between a child and parent tag.
        # i.e. Abrams is a parent to Siphon Life, and a child to Hero
        # tags below are after _remap_tag() is called
        # key = parent
        # value = children
        # also see self.parent_lookup
        self.tag_tree = {
            'Item': {
                'Weapon Item': {},
                'Vitality Item': {},
                'Spirit Item': {},
                'Flex Slot': {},
            },
            'Hero': {'Ability': {}, 'Weapon': {}},
            'Melee': {
                'Light Melee': {},
                'Heavy Melee': {},
                'Parry': {},
            },
            'NPC': {'Creep': {'Denizen': {}, 'Trooper': {}}, 'Mid-Boss': {}},
            'Objective': {
                'Guardian': {},
                'Base Guardian': {},
                'Walker': {},
                'Patron': {'Weakened Patron': {}},
                'Shrine': {},
            },
            'Souls': {'Soul Orb': {}, "Sinner's Sacrifice": {}, 'Soul Urn': {}},
            'Breakable': {'Crate': {}, 'Golden Statue': {}},
            'Shop': {},
            'Map': {
                'Department Store': {},
                'Arcade': {},
                'Fish Market': {},
                'Basement': {},
                'Bridge': {},
                'Hotel': {},
                'Pharmacy': {},
                'Penn Station': {},
                'Grand Central': {},
                'Pit': {},
                'Greenwich': {},
                'York Avenue': {},
                'Broadway': {},
                'Park Avenue': {},
            },
            'Powerup': {},
            'Zipline': {},
            'Rejuvenator': {},
            'Cosmic Veil': {},
            'Team': {
                'Sapphire Hand': {},
                'Amber Hand': {},
            },
            'Sandbox': {},
            'Pause': {},
            'Bounce Pad': {},
            'Rope': {},
            'Other': {},
        }

        self.parent_lookup = {}
        # create parent_lookup lookup table from self.tag_tree
        # key = child
        # value = list of parents
        self._build_parent_lookup_map(parent=None, children=self.tag_tree)

        # Write tag tree to file
        self._write_tag_tree(self.tag_tree)

    def _build_parent_lookup_map(self, parent, children):
        """
        From the self.tag_tree dict, transform it into a 1-layer
        lookup table where the key is a child tag and the value is a list of its parent tags
        """

        for child, grand_children in children.items():
            if parent is not None:
                if child not in self.parent_lookup:
                    self.parent_lookup[child] = [parent]
                else:
                    self.parent_lookup[child].append(parent)

            self._build_parent_lookup_map(child, grand_children)

    def _write_tag_tree(self, tag_tree):
        # Add <hero>, <ability>, <item> etc. to tag tree
        # to show where instance tags would appear (such as Abrams, Basic Magazine, Siphon Life)
        tag_tree['Hero']['<Hero Name>'] = {}
        tag_tree['Hero']['<HeroLab Hero Name>'] = {'HeroLab <HeroLab Hero Name>': {}}
        tag_tree['Hero']['Ability']['<Ability Name>'] = {}
        tag_tree['Item']['Weapon Item']['<Weapon Item Name>'] = {}
        tag_tree['Item']['Vitality Item']['<Vitality Item Name>'] = {}
        tag_tree['Item']['Spirit Item']['<Spirit Item Name>'] = {}

        json_utils.write(self.OUTPUT_CHANGELOGS + '/tag_tree.json', tag_tree)
