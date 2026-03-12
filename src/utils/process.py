import subprocess
import os
import sys
from loguru import logger


def get_executable_path(executable: str) -> str:
    """Resolve executable path, handling PyInstaller's frozen environment."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle — use the directory of the executable
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    full_path = os.path.join(base_path, executable)
    return full_path if os.path.exists(full_path) else executable  # fallback to PATH


def run_process(params, name=''):
    """Runs a subprocess with the given parameters and logs its output line by line

    Args:
        params (list[str] | str): The command and arguments to execute
        name (str, optional): An optional name to identify the process in logs. Defaults to ''
    """
    try:
        # Handle shell scripts on Windows by explicitly using bash
        if isinstance(params, str) and params.endswith('.sh') and os.name == 'nt':
            params = ['bash', params]
        elif isinstance(params, list) and len(params) > 0 and params[0].endswith('.sh') and os.name == 'nt':
            params = ['bash'] + params

        # Resolve the executable path when frozen
        if isinstance(params, list) and params:
            params = [get_executable_path(params[0])] + params[1:]
        elif isinstance(params, str) and not params.endswith('.sh'):
            params = get_executable_path(params)

        # PyInstaller sets this env var which can break child processes
        env = os.environ.copy()
        if getattr(sys, 'frozen', False):
            # Remove the PyInstaller temp path so subprocesses don't inherit it
            env.pop('_MEIPASS', None)
            # Ensure the exe's directory is on PATH so bundled tools are found
            exe_dir = os.path.dirname(sys.executable)
            env['PATH'] = exe_dir + os.pathsep + env.get('PATH', '')

        process = subprocess.Popen(
            params,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

        with process.stdout:
            for line in iter(process.stdout.readline, ''):
                logger.trace(f'[process: {name}] {line.strip()}')

    except Exception as e:
        raise Exception(f'Failed to run {name} process') from e

    exit_code = process.wait()
    if exit_code != 0:
        raise Exception(f'Process {name} exited with code {exit_code}')
