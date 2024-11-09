# Adding input-data

## Changelogs
### Historical changelogs
The RSS feed that stores previous forum changelog posts <https://forums.playdeadlock.com/forums/changelog.10/> only stores the latest few months of changelogs. As such, older changelogs have been added here manually already.

### Herolab changelogs
Hero lab changelogs do not exist on the forum, and only exist in game. The patch notes for it need to be created in its own file in `input-data/raw-changelogs/here.txt`, with the file name formatted as `herolab_yyyy_mm_dd.txt`. See the content of `input-data/raw-changelogs/herolab_2024_10_29.txt` for an example.

Add the configuration for the hero lab changelog to `input-data/changelogs.json`

# Note
Note that the paths involving `input-data` are assuming the `inputdir` parameter is defaulted.