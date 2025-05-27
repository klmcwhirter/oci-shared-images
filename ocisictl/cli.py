'''The ocisictl command line interface'''

import argparse
from ocisictl.models import AppConfig, AppContext


def parse_args(args: list[str]) -> AppContext:
    config_file = 'ocisictl.yaml'

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', default=config_file, metavar='FILE', help='FILE from which to load configuration')
    parser.add_argument('-p', '--prune', default=False, action='store_true',
                        help='Stop containers and perform system pruning before starting, and clean up artifacts after done')
    parser.add_argument('-s', '--show_layers', default=False, action='store_true', help='Show layers of images')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='Enable verbose output')

    parsed_args = parser.parse_args()

    app_config = AppConfig.from_yaml(parsed_args.file)
    return AppContext(args=parsed_args, config=app_config)
