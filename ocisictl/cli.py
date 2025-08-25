"""The ocisictl command line interface"""

import argparse

from ocisictl.models import AppContext


def parse_args(args: list[str]) -> AppContext:
    config_file = 'ocisictl.yaml'

    parser = argparse.ArgumentParser()

    verbs = parser.add_subparsers(title='verbs', required=True, dest='verb', metavar='(list | process | clean)')

    ls_desc = 'List information about the configuration or the system'
    ls = verbs.add_parser('list', description=ls_desc, help=ls_desc, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    meg = ls.add_mutually_exclusive_group(required=True)
    meg.add_argument('--all', default=False, action='store_true', help='list all images containers')
    meg.add_argument('-a', '--assemble', default=False, action='store_true', help='list containers to assemble')
    meg.add_argument('-e', '--enabled', default=False, action='store_true', help='list images to create')
    meg.add_argument('-l', '--layers', default=False, action='store_true', help='list layers of images')

    ls.add_argument('-f', '--file', default=config_file, metavar='FILE', help='configuration FILE')
    ls.add_argument('-v', '--verbose', default=False, action='store_true', help='enable verbose output')

    proc_desc = 'Create images / assemble containers'
    proc = verbs.add_parser(
        'process', description=proc_desc, help=proc_desc, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    proc.add_argument('-f', '--file', default=config_file, metavar='FILE', help='configuration FILE')
    proc.add_argument(
        '-p', '--prune', default=False, action='store_true', help='stop containers and perform system pruning before starting; if --podman is not set skip it'
    )
    proc.add_argument('--podman', default=False, action='store_true', help='clean up buildx artifacts for podman after done')
    proc.add_argument('-s', '--skip-clean', default=False, action='store_true', help='skip the clean up artifacts step after done')
    proc.add_argument('-v', '--verbose', default=False, action='store_true', help='enable verbose output')

    clean_desc = 'Clean up images'
    clean = verbs.add_parser(
        'clean', description=clean_desc, help=clean_desc, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    clean.add_argument('-f', '--file', default=config_file, metavar='FILE', help='configuration FILE')
    clean.add_argument('--podman', default=False, action='store_true', help='clean up buildx artifacts for podman after done')
    clean.add_argument('-v', '--verbose', default=False, action='store_true', help='enable verbose output')

    pargs = parser.parse_args(args=args)

    return AppContext.from_args(args=pargs)
