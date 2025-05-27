
import logging
from functools import wraps
import subprocess

from ocisictl.models import AppContext


def cmd_output_to_terminal(cmd: str, ctx: AppContext, verbose=True) -> int:
    if verbose:
        logging.info(cmd)

    return subprocess.call(cmd, shell=True, text=verbose)


def cmd_with_output(cmd: str, ctx: AppContext, verbose=True) -> str:
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
