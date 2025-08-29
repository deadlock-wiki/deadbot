import subprocess
from loguru import logger


def run_process(params, name=''):
    """Runs a subprocess with the given parameters and logs its output line by line

    Args:
        params (list[str] | str): The command and arguments to execute
        name (str, optional): An optional name to identify the process in logs. Defaults to ''

    Returns:
        str: Output from process
    """
    try:
        process = subprocess.Popen(  # noqa: F821
            params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        with process.stdout:
            for line in iter(process.stdout.readline, ''):
                logger.trace(f'[process: {name}] {line.strip()}')

    except Exception as e:
        raise Exception(f'Failed to run {name} process', e)

    process.wait()
    return process.stdout.decode('utf-8')
