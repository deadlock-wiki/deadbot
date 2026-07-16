from collections import Counter
from loguru import logger


class StreetBrawlParser:
    """
    Parses Street Brawl item draft bucketing from hero data into a flat,
    deviation-only structure under "item-buckets".

    In the Street Brawl game mode players draft items from a random selection
    instead of buying them. Every hero shares the same pool of draftable items
    (AvailableItems), and by default each item sits in the "Normal" bucket at
    weight 1.0. Heroes deviate from that default for a subset of items:
        - a different bucket (e.g. "Good", offered more often),
        - a reduced weight (e.g. 0.4, offered less often within its bucket),
        - a counter weight (a separate per-hero multiplier for specific items).

    Only these deviations are stored, as a flat list of (Hero, Item) rows that
    each carry whichever of Bucket/Weight/Counter differ from the default. The
    full per-hero bucketing is reconstructed as: every AvailableItem is
    "Normal" @ 1.0 unless a matching outlier row overrides it.

    Source fields (per hero, in heroes.json):
        m_mapItemDraftBucketing:      item -> {m_strBucket, m_flWeight}
        m_mapItemDraftCounterWeights: item -> weight (a raw float)
    """

    DEFAULT_BUCKET = 'Normal'
    DEFAULT_WEIGHT = 1.0

    def __init__(self, heroes_data):
        self.heroes_data = heroes_data

    def run(self):
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
            'item-buckets': {
                'AvailableItems': sorted(available_items),
                'Defaults': {'Bucket': self.DEFAULT_BUCKET, 'Weight': self.DEFAULT_WEIGHT},
                'Outliers': outliers,
            }
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
