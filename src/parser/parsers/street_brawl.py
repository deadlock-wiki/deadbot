from collections import Counter
from loguru import logger

from utils import json_utils
from .abilities import AbilityParser


class StreetBrawlParser:
    """
    Parses Street Brawl deviations from the normal game into "street-brawl-data.json".

    "ability-changes"
        Some ability stats have a Street-Brawl-only value e.g. a longer cooldown or a
        smaller radius.
        We re-run the ability parser on a copy of the data with those swaps
        applied, then keep only the leaves that differ from the normal parse, so
        an entry lists exactly the stats that change. Each kept
        leaf sits at the same key path as in ability-data.json, so a Street
        Brawl value can be referenced the same way as its normal counterpart,
        e.g. {{data|streetbrawl|A|AbilityCooldown}} vs {{data|abilities|A|AbilityCooldown}}.

    "item-buckets"
        Every hero shares the same pool of draftable items
        (AvailableItems), and by default each item sits in the "Normal" bucket
        at weight 1.0. Heroes deviate from that default for a subset of items:
            - a different bucket (e.g. "Good", offered more often),
            - a reduced weight (e.g. 0.4, offered less often within its bucket),
            - a counter weight (a separate per-hero multiplier for specific items).
        Only these deviations are stored, as a flat list of (Hero, Item) rows
        that each carry whichever of Bucket/Weight/Counter differ from the
        default. The full per-hero bucketing is reconstructed as: every
        AvailableItem is "Normal" @ 1.0 unless a matching outlier row overrides it.
    """

    DEFAULT_BUCKET = 'Normal'
    DEFAULT_WEIGHT = 1.0

    # Street-Brawl-only override -> the base ability-property key it replaces.
    OVERRIDE_KEYS = {
        'm_strStreetBrawlValue': 'm_strValue',
        'm_flStreetBrawlStatScale': 'm_flStatScale',
        'm_strStreetBrawlBonus': 'm_strBonus',
    }

    # Sentinel meaning "these two nodes are identical", distinct from a real
    # None/empty value that could legitimately appear in the parsed data.
    _NO_DIFF = object()

    def __init__(self, heroes_data, abilities_data, base_abilities, localizations):
        self.heroes_data = heroes_data
        self.abilities_data = abilities_data
        self.base_abilities = base_abilities
        self.localizations = localizations

    def run(self):
        return {
            'ability-changes': self._parse_ability_changes(),
            'item-buckets': self._parse_item_buckets(),
        }

    # --- Ability changes -------------------------------------------------

    def _parse_ability_changes(self):
        """
        Re-parse abilities with Street Brawl overrides swapped in, then keep
        only the values that differ from the normal parse.
        """
        brawl_raw = json_utils.wrap_case_insensitive(self._apply_overrides(self.abilities_data))
        brawl_abilities = AbilityParser(brawl_raw, self.heroes_data, self.localizations).run()

        changes = {}
        for key, brawl_ability in brawl_abilities.items():
            base_ability = self.base_abilities.get(key)
            if base_ability is None:
                continue

            delta = self._diff(base_ability, brawl_ability)
            if not delta:
                continue

            # Name is unchanged so the diff drops it; re-attach so editors can
            # see which ability an entry is without a second lookup. Its changed
            # stats sit as siblings, keyed exactly as in ability-data.json.
            changes[key] = {'Name': brawl_ability.get('Name'), **delta}

        return json_utils.sort_dict(changes)

    def _apply_overrides(self, node):
        """
        Deep-copy the raw ability tree into plain dicts, replacing each base
        value with its Street Brawl override where one is present. Returns
        plain dicts so the result can be re-wrapped case-insensitively without
        depending on deepcopy semantics of CaseInsensitiveDict.
        """
        if isinstance(node, dict):
            out = {key: self._apply_overrides(value) for key, value in node.items()}
            for override_key, base_key in self.OVERRIDE_KEYS.items():
                if override_key in node:
                    override = node[override_key]
                    # An empty/None override is a placeholder ("unset in Street
                    # Brawl"), not a real value. Applying it would emit a useless
                    # "" that can't back a {{data}} reference, so leave the base
                    # value in place and let this property fall out of the diff.
                    if override is None or override == '':
                        continue
                    out[base_key] = self._apply_overrides(override)
            return out
        if isinstance(node, list):
            return [self._apply_overrides(item) for item in node]
        return node

    def _diff(self, base, brawl):
        result = self._diff_node(base, brawl)
        return {} if result is self._NO_DIFF else result

    def _diff_node(self, base, brawl):
        """
        Return the parts of ``brawl`` that differ from ``base``, preserving the
        original nesting, or ``_NO_DIFF`` when the two are identical.
        """
        if isinstance(base, dict) and isinstance(brawl, dict):
            out = {}
            for key, brawl_value in brawl.items():
                if key in base:
                    sub = self._diff_node(base[key], brawl_value)
                    if sub is not self._NO_DIFF:
                        out[key] = sub
                else:
                    out[key] = brawl_value
            return out or self._NO_DIFF

        # Same-length lists are positional (e.g. Upgrades tiers). Collapse to an
        # object keyed by the changed positions only, so unchanged tiers vanish
        # instead of leaving empty placeholders the editor has to count past.
        # Keys are 1-based to line up with Lua's 1-indexed arrays, so the same
        # index addresses this tier in ability-data.json's Upgrades list.
        if isinstance(base, list) and isinstance(brawl, list) and len(base) == len(brawl):
            changed = {}
            for index, (base_item, brawl_item) in enumerate(zip(base, brawl)):
                sub = self._diff_node(base_item, brawl_item)
                if sub is not self._NO_DIFF:
                    changed[str(index + 1)] = sub
            return changed or self._NO_DIFF

        return brawl if base != brawl else self._NO_DIFF

    # --- Item draft bucketing --------------------------------------------

    def _parse_item_buckets(self):
        available_items = set()
        outliers = []

        for hero_key, hero_data in self.heroes_data.items():
            if not hero_key.startswith('hero') or hero_key == 'hero_base':
                continue

            bucketing = hero_data.get('m_mapItemDraftBucketing')
            if not bucketing:
                continue

            counter_weights = hero_data.get('m_mapItemDraftCounterWeights') or {}
            self._warn_if_default_shifted(hero_key, bucketing)

            for item_key, entry in bucketing.items():
                available_items.add(item_key)

                row = {}
                if entry['m_strBucket'] != self.DEFAULT_BUCKET:
                    row['Bucket'] = entry['m_strBucket']
                if entry['m_flWeight'] != self.DEFAULT_WEIGHT:
                    row['Weight'] = entry['m_flWeight']
                if item_key in counter_weights:
                    row['Counter'] = counter_weights[item_key]

                if row:
                    outliers.append({'Hero': hero_key, 'Item': item_key, **row})

            # Defensive: a counter weight on an item outside the bucketing map
            # would otherwise be dropped. None exist today, but keep it robust.
            for item_key, counter in counter_weights.items():
                if item_key not in bucketing:
                    available_items.add(item_key)
                    outliers.append({'Hero': hero_key, 'Item': item_key, 'Counter': counter})

        outliers.sort(key=lambda row: (row['Hero'], row['Item']))

        return {
            'AvailableItems': sorted(available_items),
            'Defaults': {'Bucket': self.DEFAULT_BUCKET, 'Weight': self.DEFAULT_WEIGHT},
            'Outliers': outliers,
        }

    def _warn_if_default_shifted(self, hero_key, bucketing):
        """
        The deviation-only encoding assumes "Normal" @ 1.0 is by far the most
        common (bucket, weight) for every hero. If that ever stops being true,
        the file stays correct but bloats, so warn to prompt a rethink.
        """
        most_common = Counter((entry['m_strBucket'], entry['m_flWeight']) for entry in bucketing.values()).most_common(1)[0][0]
        if most_common != (self.DEFAULT_BUCKET, self.DEFAULT_WEIGHT):
            logger.warning(
                f'Street Brawl: {hero_key} most-common bucket/weight is {most_common}, '
                f'not the assumed default ({self.DEFAULT_BUCKET}, {self.DEFAULT_WEIGHT}). '
                'Consider revisiting the deviation-only encoding in [[Module:StreetBrawl]].'
            )
