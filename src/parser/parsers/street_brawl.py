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
        Every hero draws from the same shop item pool (AvailableItems).
        Items default to the "Normal" bucket at weight 1.0. An item without an
        explicit bucket is instead "Good" when its best pick percentage across
        the game phases reaches the tier's threshold from generic_data. Heroes
        can also override an item's bucket, weight, or counter weight. Only
        deviations are stored, as a flat list of (Hero, Item) rows carrying
        whichever of Bucket/Weight/Counter differ from the default. The tier
        thresholds and bucket weights are exposed under TierBuckets.
    """

    DEFAULT_BUCKET = 'Normal'
    DEFAULT_WEIGHT = 1.0

    # Street-Brawl-only override -> the base ability-property key it replaces.
    OVERRIDE_KEYS = frozenset(
        {
            ('m_strStreetBrawlValue', 'm_strValue'),
            ('m_flStreetBrawlStatScale', 'm_flStatScale'),
            ('m_strStreetBrawlBonus', 'm_strBonus'),
        }
    )

    # Sentinel meaning "these two nodes are identical", distinct from a real
    # None/empty value that could legitimately appear in the parsed data.
    _NO_DIFF = object()

    def __init__(self, heroes_data, abilities_data, base_abilities, localizations, items_data, generic_data):
        self.heroes_data = heroes_data
        self.abilities_data = abilities_data
        self.base_abilities = base_abilities
        self.localizations = localizations
        self.items_data = items_data
        self.generic_data = generic_data

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
            for override_key, base_key in self.OVERRIDE_KEYS:
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

    def _item_tier(self, item_key):
        item = self.items_data.get(item_key) or {}
        tier = item.get('Tier')
        return tier if isinstance(tier, int) and tier > 0 else None

    def _shop_item_keys(self):
        """
        The draft pool is every shop item in a draft tier. Items without a shop
        icon are internal bases (e.g. armor_upgrade_t1), not shop entries.
        """
        keys = set()
        for item_key, item in self.items_data.items():
            if item.get('IsDisabled') or self._item_tier(item_key) is None:
                continue
            raw_item = self.abilities_data.get(item_key) or {}
            if raw_item.get('m_strShopIconLarge'):
                keys.add(item_key)
        return keys

    def _tier_bucket_config(self):
        street_brawl = self.generic_data.get('m_StreetBrawl') or {}
        buckets = street_brawl.get('m_mapItemTierToItemDraftBuckets') or {}
        config = {}
        for key, value in buckets.items():
            if not key.startswith('EModTier_'):
                continue
            try:
                tier = int(key[len('EModTier_'):])
            except ValueError:
                continue
            config[tier] = value
        return config

    def _hero_popularity(self, hero_data):
        popular = hero_data.get('m_PopularItems') or {}
        generated = popular.get('m_mapGeneratedItemPopularity') or {}
        manual = popular.get('m_mapManualItemPopularity') or {}

        phases = {phase: dict(entries or {}) for phase, entries in generated.items()}
        for phase, entries in manual.items():
            phases.setdefault(phase, {}).update(entries or {})
        return phases

    def _best_pick_pct(self, popularity, item_key):
        best = 0.0
        for entries in popularity.values():
            entry = entries.get(item_key) or {}
            pick = entry.get('m_flPickPct')
            if isinstance(pick, (int, float)):
                best = max(best, float(pick))
        return best

    def _parse_item_buckets(self):
        available_items = self._shop_item_keys()
        tier_buckets = self._tier_bucket_config()
        default_threshold = 100.0
        outliers = []

        # A hero override can name an item that is not in the shop-icon pool.
        # Keep those rows rather than silently dropping them.
        for hero_data in self.heroes_data.values():
            if not isinstance(hero_data, dict):
                continue
            available_items.update((hero_data.get('m_mapItemDraftBucketing') or {}).keys())
            available_items.update((hero_data.get('m_mapItemDraftCounterWeights') or {}).keys())

        for hero_key, hero_data in self.heroes_data.items():
            if not hero_key.startswith('hero') or hero_key == 'hero_base':
                continue
            if not isinstance(hero_data, dict):
                continue

            bucketing = hero_data.get('m_mapItemDraftBucketing') or {}
            counter_weights = hero_data.get('m_mapItemDraftCounterWeights') or {}
            popularity = self._hero_popularity(hero_data)

            for item_key in available_items:
                entry = bucketing.get(item_key) or {}
                tier_config = tier_buckets.get(self._item_tier(item_key)) or {}

                bucket = entry.get('m_strBucket')
                if not bucket:
                    threshold = tier_config.get('m_flGoodItemPickRateThreshold', default_threshold)
                    if not isinstance(threshold, (int, float)):
                        threshold = default_threshold
                    best_pick = self._best_pick_pct(popularity, item_key)
                    bucket = 'Good' if best_pick >= threshold else self.DEFAULT_BUCKET

                row = {}
                if bucket != self.DEFAULT_BUCKET:
                    row['Bucket'] = bucket

                weight = entry.get('m_flWeight', self.DEFAULT_WEIGHT)
                if isinstance(weight, (int, float)) and weight != self.DEFAULT_WEIGHT:
                    row['Weight'] = weight

                if item_key in counter_weights:
                    row['Counter'] = counter_weights[item_key]

                if row:
                    outliers.append({'Hero': hero_key, 'Item': item_key, **row})

        outliers.sort(key=lambda row: (row['Hero'], row['Item']))

        tier_config_out = {}
        for tier, config in sorted(tier_buckets.items()):
            tier_config_out[str(tier)] = {
                'Name': config.get('m_strBucketName', ''),
                'Buckets': dict(config.get('m_mapBuckets') or {}),
                'GoodPickRateThreshold': config.get('m_flGoodItemPickRateThreshold', default_threshold),
            }

        return {
            'AvailableItems': sorted(available_items),
            'Defaults': {'Bucket': self.DEFAULT_BUCKET, 'Weight': self.DEFAULT_WEIGHT},
            'TierBuckets': tier_config_out,
            'Outliers': outliers,
        }
