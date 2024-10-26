import pandas as pd
import os


def load_game_info(game_info_path):
    """
    Loads steam game version info from steam.inf file.

    Args:
        game_info_path (str): path of the version file.  Usually named steam.inf or version.txt

    Returns:
        dict of versions
    """
    version_info = {}
    try:
        with open(game_info_path, 'r') as f:
            for line in f.readlines():
                split_line = line.strip().split('=')
                # first item is the key, the rest are the value in case there's multiple `=`
                version_info[split_line[0]] = split_line[1]
    except:
        print(f'[ERROR]: Issue opening game info file at {game_info_path}')
    return version_info
