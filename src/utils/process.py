import subprocess
import os
import sys
from loguru import logger


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

        process = subprocess.Popen(  # noqa: F821
            params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        with process.stdout:
            for line in iter(process.stdout.readline, ''):
                logger.trace(f'[process: {name}] {line.strip()}')

    except Exception as e:
        raise Exception(f'Failed to run {name} process', e)

    exit_code = process.wait()
    if exit_code != 0:
        raise Exception(f'Process {name} exited with code {exit_code}')

def get_resource_path(relative_path):
    """Get the correct path for a resource, works for both dev and PyInstaller binary"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    # Running in normal Python environment
    return os.path.join(os.path.dirname(__file__), relative_path)
