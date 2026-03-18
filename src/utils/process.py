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
        # Resolve resource path for string params before any wrapping
        if isinstance(params, str):
            process_path = get_resource_path(params)
        else:
            process_path = params

        # Handle shell scripts on Windows by explicitly using bash
        if isinstance(process_path, str) and process_path.endswith('.sh') and os.name == 'nt':
            process_path = ['bash', process_path]
        elif (
            isinstance(process_path, list)
            and len(process_path) > 0
            and isinstance(process_path[0], str)
            and process_path[0].endswith('.sh')
            and os.name == 'nt'
        ):
            process_path = ['bash'] + process_path

        process = subprocess.Popen(  # noqa: F821
            process_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        with process.stdout:
            for line in iter(process.stdout.readline, ''):
                logger.trace(f'[process: {name}] {line.strip()}')

    except Exception as e:
        raise Exception(f'Failed to run {name} process', e)

    exit_code = process.wait()
    if exit_code != 0:
        raise Exception(f'Process {name} exited with code {exit_code}')


_SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(script_params):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, script_params)
    return os.path.join(_SRC_ROOT, script_params)
