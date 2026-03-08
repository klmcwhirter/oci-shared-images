
import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping

from rich import box
from rich.console import Console
from rich.table import Table

BFIN_PROBLEM_BINS = [
    'fastfetch',
    'fzf',
    'jq',
    'node',
    'npm',
    'npx',
    'pnpm',
    'pnpx',
    'uv',
    'uvx',
    'zoxide'
]

LOCAL_BIN = Path('~/.local/bin').expanduser().resolve()


def cmp_bin4exported(bin: Path, bins: list[str], is_bluefin: bool) -> Mapping[str, tuple[bool, bool, bool]]:
    paths = {lbf for lbf in bin.iterdir() if lbf.is_file()}
    paths.update(LOCAL_BIN / name for name in BFIN_PROBLEM_BINS)

    exported_apps = {
        lbf.name: (
            is_bluefin and lbf.name in bins,
            lbf.exists(),
            grep(lbf, 'distrobox-enter')
        )
        for lbf in paths
    }

    return {
        k: exported_apps[k]
        for k in sorted(exported_apps)
    }


def grep(path: Path, expr: str) -> bool:
    return subprocess.call(f'grep {expr} {path} >/dev/null 2>&1', shell=True) == 0


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--all', default=False, action='store_true', help=f'List all files in {LOCAL_BIN}')
    parser.add_argument('-d', '--delete', default=False, action='store_true',
                        help=f'delete all files in {LOCAL_BIN} that might cause an problem if running on bluefin host')
    return parser.parse_args(args)


def is_bluefin_host() -> bool:
    file_path = Path('/etc/os-release')

    return file_path.exists() and grep(file_path, 'bluefin')


def main(args: list[str]) -> None:
    ns = parse_args(args)
    cli_all = ns.all
    cli_delete = ns.delete

    console = Console()
    is_bluefin = is_bluefin_host()

    table = Table(title=f'Bluefin Problematic Exported Binaries in {LOCAL_BIN}\n{is_bluefin=}', title_justify='left', show_lines=True, box=box.ROUNDED)
    table.add_column('Name')
    table.add_column('Problem?', justify='center', style='bold green1')
    table.add_column('Exists?', justify='center', style='bold green1')
    table.add_column('Exported?', justify='center', style='bold green1')

    tbl_data = cmp_bin4exported(LOCAL_BIN, BFIN_PROBLEM_BINS, is_bluefin)

    delete_files: list[str] = []

    for local_path, (problem, exists, exported) in tbl_data.items():
        if cli_all or problem:
            table.add_row(
                os.path.basename(local_path),
                '+' if problem else '',
                '+' if exists else '',
                '+' if exported else '',
            )
            if is_bluefin and cli_delete and exported and problem:
                delete_files.append(local_path)

    console.print(table)

    for f in delete_files:
        print(f'deleted {f}')
        os.unlink(f)


if __name__ == '__main__':
    main(sys.argv[1:])
