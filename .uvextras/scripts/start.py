# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///


import os
import subprocess
import sys

# prevent warning that VIRTUAL_ENV is different
del os.environ['VIRTUAL_ENV']

cmd = f'uv run python -m ocisictl {' '.join(sys.argv[1:])}'
subprocess.call(f'{cmd}', shell=True, text=True)
