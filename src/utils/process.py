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
    if isinstance(params, str) and params.endswith('.sh') and os.name == 'nt':
        params = ['bash', params]
    elif isinstance(params, list) and len(params) > 0 and params[0].endswith('.sh') and os.name == 'nt':
        params = ['bash'] + params

    if sys.platform == 'win32':
        params = convert_to_wsl_params(params)

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


def convert_to_wsl_params(params):
    def to_wsl_path(p):
        if isinstance(p, str) and len(p) >= 2 and p[1] == ':':
            result = subprocess.run(['wsl', 'wslpath', p.replace('\\', '/')], capture_output=True, text=True)
            return result.stdout.strip()
        return p

    wsl_binary = to_wsl_path(params[0])
    converted_args = [to_wsl_path(p) for p in params[1:]]  # ← this line is the critical addition

    return ['wsl', wsl_binary] + converted_args
