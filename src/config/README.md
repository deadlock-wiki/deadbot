#TODO make this better

1. Create `src/config/user_config.json`
2. Add path value for key `deadlock_path` and `decompiler_path` in the json by hand
OR
2. Use the following command for each: `python /src/config/config_manager.py --set deadlock_path "/path/to/user/deadlock/path"`

Example user_config.json
{
    "deadlock_path": "C:\\SteamLibrary\\steamapps\\common\\Deadlock",
    "decompiler_path": "C:\\Users\\eetha\\Downloads\\Decompiler-windows-x64"
}