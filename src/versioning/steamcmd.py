import subprocess

class SteamCMD:
    """
    SteamCMD is a Valve tool that allows some steam operations from the command line

    This class is used to retrieve the most recent manifest-id for Deadlock
    """
    def __init__(self, steam_cmd_path, app_id):
        self.STEAM_CMD_PATH = steam_cmd_path
        self.APP_ID = app_id
        self.DEPOT_ID = 1422456
    
    def run(self):
        # Run steamcmd, save terminal output
        output = subprocess.run([self.STEAM_CMD_PATH, 
                                 "+login anonymous", 
                                 "+app_info_update 0", 
                                 f"+app_info_print {self.APP_ID}", 
                                 "+logout", 
                                 "+quit"],
                                stdout=subprocess.PIPE)
        output_str = output.stdout.decode('utf-8')

        # Search the vdata string repeatedly for these keywords, similar to navigating a JSON object
        keywords = [str(self.APP_ID), 
                    '"common"', 
                    '"depots"', 
                    f'"{str(self.DEPOT_ID)}"', 
                    '"manifest"', 
                    '"public"', 
                    '"gid"', 
                    '"']
        for keyword in keywords:
            output_str = get_str_after_keyword(keyword, output_str)
        # output_str should now start with the manifest id, followed by a " and other text

        # Extract the manifest id
        manifest_id = output_str.split('"')[0]

        return manifest_id

# Returns the string after the first instance of a keyword
# Example: get_str_after_keyword("manifest", "depots 1234 manifest 5678") returns " 5678"
def get_str_after_keyword(keyword, string):
    keyword_index = string.find(keyword)
    return string[keyword_index+len(keyword):]