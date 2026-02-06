import re
from datetime import datetime
from typing import List, Tuple, Optional


def sort_changelog_files(files: List[str]) -> List[str]:
    """
    Sort changelog files with proper variant ordering.
    Base file comes before variants.
    """

    def sort_key(filename):
        base = filename.replace('.txt', '')
        parts = base.split('-')
        # parts[0:3] = ['2026', '01', '30'], parts[3] = '1' or missing
        date_tuple = (int(parts[0]), int(parts[1]), int(parts[2])) if len(parts) >= 3 else (0, 0, 0)
        # variant = 0 for base file, N for -N variants
        variant = int(parts[3]) if len(parts) > 3 else 0
        return (date_tuple, variant)

    return sorted(files, key=sort_key)


def parse_changelog_date_from_id(changelog_id: str) -> Optional[datetime]:
    """Parse date from changelog ID like '2026-01-30' or '2026-01-30-1'."""
    try:
        parts = changelog_id.split('-')
        # Handle both 'YYYY-MM-DD' and 'YYYY-MM-DD-N' formats
        date_part = '-'.join(parts[:3])
        return datetime.strptime(date_part, '%Y-%m-%d')
    except (ValueError, IndexError):
        return None


def calculate_prev_update_link(
    date_obj: datetime,
    current_title: str,
    wiki_updates: List[Tuple[datetime, str]],
    uploads_this_run: List[Tuple[datetime, str]] = None,
) -> str:
    """
    Calculate the correct prev_update link by querying actual wiki state plus uploads in current run.
    Uses <= for date comparison to handle same-date variants.
    Returns formatted {{Update link|...}} string or empty string if no previous update.
    """
    # Include entries with same date (for variants) but exclude self
    all_candidates = [(d, t) for d, t in wiki_updates if d <= date_obj and t != current_title]

    if uploads_this_run:
        all_candidates.extend([(d, t) for d, t in uploads_this_run if d <= date_obj and t != current_title])

    # Filter to only those strictly earlier OR same date with earlier variant
    earlier_dates = [(d, t) for d, t in all_candidates if d < date_obj]
    same_date = [(d, t) for d, t in all_candidates if d == date_obj]

    # Prefer strictly earlier dates; only use same-date if no earlier dates exist
    final_candidates = earlier_dates if earlier_dates else same_date

    if not final_candidates:
        return ''

    # Get the most recent one among them
    final_candidates.sort(key=lambda x: x[0])
    prev_date, _ = final_candidates[-1]

    # Format: {{Update link|Month|Day|Year}}
    return f"{{{{Update link|{prev_date.strftime('%B')}|{prev_date.day}|{prev_date.year}}}}}"


def inject_prev_update(content: str, prev_update_link: str) -> str:
    """
    Inject the correct prev_update link into the wikitext content.
    Replaces any existing prev_update value or adds if missing.
    """
    if not prev_update_link:
        # If no previous update, ensure prev_update is empty
        pattern = r'(\|\s*prev_update\s*=\s*)(.*?)(?=\n\||\n\}\}|\Z)'
        return re.sub(pattern, r'\1', content, count=1, flags=re.DOTALL)

    # Check if prev_update field exists
    pattern = r'(\|\s*prev_update\s*=\s*)(.*?)(?=\n\||\n\}\}|\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        # Replace existing value
        return re.sub(pattern, rf'\1{prev_update_link}', content, count=1, flags=re.DOTALL)
    else:
        # Add prev_update field after the template opening
        layout_match = re.search(r'(\{\{\s*Update\s+layout\s*\n)', content)
        if layout_match:
            insert_pos = layout_match.end()
            return content[:insert_pos] + f'| prev_update = {prev_update_link}\n' + content[insert_pos:]
        else:
            # Fallback: prepend to content
            return f'| prev_update = {prev_update_link}\n' + content
