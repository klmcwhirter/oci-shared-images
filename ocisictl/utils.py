
import logging
import subprocess
from functools import wraps


def cmd_output_to_terminal(cmd: str, verbose=True) -> int:
    if verbose:
        logging.info(cmd)

    return subprocess.call(cmd, shell=True, text=verbose)


def cmd_with_output(cmd: str, verbose=True) -> str:
    if verbose:
        logging.info(cmd)

    return subprocess.check_output(cmd, shell=True, text=True)


def log_entry_exit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.debug(f'{func.__name__} starting')
        rc = func(*args, **kwargs)
        logging.debug(f'{func.__name__} done')
        return rc
    return wrapper
