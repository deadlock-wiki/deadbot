import requests
from loguru import logger


def send_wiki_update_notification(webhook_url: str, upload_summary: dict, dry_run: bool = False):
    if not webhook_url:
        logger.trace('No Discord webhook URL configured, skipping notification')
        return

    if dry_run:
        logger.info('Dry run: skipping Discord notification')
        return

    data_pages_updated = upload_summary.get('data_pages_updated', 0)
    changelogs_uploaded = upload_summary.get('changelogs_uploaded', [])
    hotfixes_applied = upload_summary.get('hotfixes_applied', [])
    game_version = upload_summary.get('game_version', 'Unknown')
    deadbot_version = upload_summary.get('deadbot_version', 'Unknown')

    fields = [
        {'name': 'Game Version', 'value': game_version, 'inline': True},
        {'name': 'Deadbot Version', 'value': f'v{deadbot_version}', 'inline': True},
        {'name': f'Data Pages Updated ({len(data_pages_updated)})', 'value': '\n'.join(data_pages_updated[:10]), 'inline': False},
    ]

    if changelogs_uploaded:
        fields.append(
            {
                'name': f'Changelogs Uploaded ({len(changelogs_uploaded)})',
                'value': '\n'.join(changelogs_uploaded[:10]),
                'inline': False,
            }
        )

    if hotfixes_applied:
        fields.append(
            {
                'name': f'Hotfixes Applied ({len(hotfixes_applied)})',
                'value': '\n'.join(hotfixes_applied[:10]),
                'inline': False,
            }
        )

    embed = {
        'title': 'Wiki Update Complete',
        'color': 5763719,  # Green
        'fields': fields,
    }

    try:
        response = requests.post(webhook_url, json={'embeds': [embed]}, timeout=10)
        response.raise_for_status()
        logger.success('Discord notification sent')
    except requests.exceptions.HTTPError as e:
        logger.error(f'Discord notification failed with HTTP error: {e}')
    except Exception as e:
        logger.error(f'Failed to send Discord notification: {e}')


def send_error_notification(webhook_url: str, error: Exception, dry_run: bool = False):
    if not webhook_url or dry_run:
        return

    embed = {
        'title': 'Wiki Update Failed',
        'description': f'```{str(error)[:1000]}```',
        'color': 15548997,  # Red
    }

    try:
        requests.post(webhook_url, json={'embeds': [embed]}, timeout=10)
    except Exception as e:
        logger.error(f'Failed to send Discord error notification: {e}')
