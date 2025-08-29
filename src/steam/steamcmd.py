import os

from utils.process import run_process
from .constants import APP_ID, DEPOT_ID


class SteamCMD:
    """
    SteamCMD is a Valve tool that allows some steam operations from the command line

    This class is used to retrieve the most recent manifest-id for Deadlock
    """

    def __init__(self, steam_cmd_path, steam_username, steam_password):
        if not steam_cmd_path:
            raise Exception('Config for SteamCMD is required')
        if not os.path.exists(steam_cmd_path):
            raise Exception(f'Could not find SteamCMD at path "{steam_cmd_path}"')

        self.STEAM_CMD_PATH = steam_cmd_path
        self.APP_ID = APP_ID
        self.DEPOT_ID = DEPOT_ID
        self.steam_username = steam_username
        self.steam_password = steam_password

    def get_latest_manifest_id(self):
        output = run_process(
            [
                self.STEAM_CMD_PATH,
                f'+login {self.steam_username} {self.steam_password}',
                '+app_info_update 0',
                f'+app_info_print {self.APP_ID}',
                '+logout',
                '+quit',
            ],
            name='SteamCMD',
        )

        # Search the vdata string repeatedly for these keywords, similar to navigating a JSON object
        keywords = [
            str(self.APP_ID),
            '"common"',
            '"depots"',
            f'"{str(self.DEPOT_ID)}"',
            '"manifest"',
            '"public"',
            '"gid"',
            '"',
        ]
        for keyword in keywords:
            output_str = get_str_after_keyword(keyword, output)
        # output_str should now start with the manifest id, followed by a " and other text

        # Extract the manifest id
        manifest_id = output_str.split('"')[0]

        if len(manifest_id) < 15:
            raise Exception('Failed to retrieve manifest id. SteamCMD output: ' + output.stdout.decode('utf-8'))

        return manifest_id


def get_str_after_keyword(keyword, string):
    """Returns the string after the first instance of a keyword

    Example:
        get_str_after_keyword("manifest", "depots 1234 manifest 5678") returns " 5678"
    """
    if keyword in string:
        keyword_index = string.find(keyword)
    else:
        raise Exception(f'Keyword "{keyword}" not found in string "{string}"')
    return string[keyword_index + len(keyword) :]
