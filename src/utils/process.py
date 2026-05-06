import subprocess
import os
import sys
from subprocess import SubprocessError

from loguru import logger


def run_process(
    params,
    name='',
    suppress_stdout=False,
):
    """Runs a subprocess with the given parameters and logs its output line by line

    Args:
        params (list[str] | str): The command and arguments to execute
        name (str, optional): An optional name to identify the process in logs. Defaults to ''
        suppress_stdout (bool, optional): If true, stdout will be returned, but not logged. Defaults to False.
    Returns: A list of lines from stdout
    """
    try:
        # Resolve resource path for string params before any wrapping
        if isinstance(params, str):
            process_path = get_resource_path(params)
        else:
            process_path = [get_resource_path(params[0])] + [str(p) for p in params[1:]]
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

        logger.trace(f'[process: {name}] Starting process with command {process_path}')
        with subprocess.Popen(process_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=_SRC_ROOT) as process:
            output_lines = []
            for line in process.stdout:
                stripped = line.strip()
                if not suppress_stdout:
                    logger.trace(f'[process: {name}] {stripped}')
                output_lines.append(stripped)

            for line in process.stderr:
                logger.trace(f'[process: {name}] {line.strip()}')
    except OSError as e:
        raise SubprocessError(f'Failed to run {name} process') from e

    exit_code = process.wait()
    if exit_code != 0:
        raise SubprocessError(f'Process {name} exited with code {exit_code}')

    return '\n'.join(output_lines)


_SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(script_params):
    # Don't remap absolute paths
    if os.path.isabs(script_params):
        return script_params

    # Used by Nuitka onefile to build binary
    if '__compiled__' in dir(__builtins__) or hasattr(sys, 'frozen'):
        base = os.path.dirname(sys.executable)
        return os.path.join(base, script_params)

    return os.path.join(_SRC_ROOT, script_params)
