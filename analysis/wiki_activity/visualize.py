import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("output/top_pages_last_7_days.csv")

plt.figure(figsize=(10, 5))
plt.barh(df["page"], df["edit_count"])
plt.xlabel("Number of Edits")
plt.title("Top 10 Most Edited Wiki Pages (Last 7 Days)")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig("output/edits_trend.png")
plt.show()