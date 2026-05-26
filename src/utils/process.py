import subprocess
import os
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
    if isinstance(params, str) and params.endswith('.sh') and os.name == 'nt':
        params = ['bash', params]
    elif isinstance(params, list) and len(params) > 0 and params[0].endswith('.sh') and os.name == 'nt':
        params = ['bash'] + params

    try:
        logger.trace(f'[process: {name}] Starting process with command {params}')
        with subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
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
