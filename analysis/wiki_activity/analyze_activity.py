import pandas as pd

df = pd.read_csv("output/revisions_raw.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

df["topic"] = df["page"].str.split("/").str[:2].str.join("/")

EXCLUDED_PREFIXES = (
    "User:",
    "Module:",
    "Template:",
    "File:",
    "Category:",
    "MediaWiki:"
)

df = df[~df["topic"].str.startswith(EXCLUDED_PREFIXES)]
df = df[~df["topic"].str.contains("Sandbox", case=False)]
df = df[~df["topic"].str.fullmatch("Movement|Death")]

page_activity = (
    df.groupby("topic")
      .size()
      .reset_index(name="edit_count")
      .sort_values("edit_count", ascending=False)
)

page_activity.to_csv("output/top_topics_last_7_days.csv", index=False)
print(page_activity.head(10))