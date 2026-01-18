import requests
import pandas as pd
from datetime import datetime, timedelta

API_URL = "https://deadlock.wiki/api.php"

def fetch_recent_revisions(days=7, limit=500):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    params = {
        "action": "query",
        "format": "json",
        "list": "recentchanges",
        "rcprop": "title|timestamp",
        "rclimit": limit,
        "rcstart": since,
        "rcdir": "newer"
    }

    response = requests.get(API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    records = [
        {
            "page": rc["title"],
            "timestamp": rc["timestamp"]
        }
        for rc in data["query"]["recentchanges"]
    ]

    return pd.DataFrame(records)

if __name__ == "__main__":
    df = fetch_recent_revisions(days=7)
    df.to_csv("output/revisions_raw.csv", index=False)