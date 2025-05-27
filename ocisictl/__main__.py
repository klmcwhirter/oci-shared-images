

import sys

from ocisictl.cli import parse_args
from ocisictl.steps import run_steps


def main(args: list[str]) -> None:
    ctx = parse_args(args=args)

    ctx.log()

    run_steps(ctx=ctx)


if __name__ == '__main__':
    main(sys.argv[1:])
