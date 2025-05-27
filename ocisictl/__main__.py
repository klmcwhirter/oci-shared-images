

import sys

from ocisictl.cli import parse_args
from ocisictl.steps import process, show_layers


def main(args: list[str]) -> None:
    ctx = parse_args(args=args)

    ctx.log()

    if (ctx.show_layers):
        show_layers(ctx=ctx)
    else:
        process(ctx=ctx)


if __name__ == '__main__':
    main(sys.argv)
