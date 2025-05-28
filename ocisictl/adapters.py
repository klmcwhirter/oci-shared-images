'''Adapter classes and functions used by steps'''


import os
import shutil
from contextlib import contextmanager
from typing import Generator

from ocisictl.utils import cmd_output_to_terminal, cmd_with_output

# _CM_OPTS = 'BUILDKIT_PROGRESS=plain '
_CM_OPTS = ''


def container_remove(manager: str, name: str, verbose: bool) -> None:
    cmd_output_to_terminal(cmd=f'{manager} rm -f --volumes {name}', verbose=verbose)


def container_stop(manager: str, name: str, verbose: bool) -> None:
    cmd_output_to_terminal(cmd=f'{manager} stop {name}', verbose=verbose)


def containers_running(manager: str, verbose: bool) -> list[str]:
    idkey = '.ID'

    if manager == 'podman':
        idkey = ".[].Id"

    return cmd_with_output(
        cmd=f'{manager} ps --format json | yq -p=j {idkey} | sed \'/---/d\'',
        verbose=verbose
    ).splitlines()


def image_build(manager: str, container_file: str, image_name: str, build_args: str, verbose: bool) -> None:
    cmd_output_to_terminal(
        cmd=f'{_CM_OPTS}{manager} buildx build -f {container_file} -t {image_name} {build_args} .',
        verbose=verbose
    )


def image_names(manager: str, verbose: bool) -> list[str]:
    cmd = ''
    if manager == 'docker':
        cmd = f'{manager} image ls --format json | yq -p=j \'select(.Repository != "<none>") | (.Repository + ":" + .Tag)\' | sed \'/---/d;/^:$/d\' | sort'  # noqa E501
    elif manager == 'podman':
        cmd = f'{manager} image ls --format json | yq -p=j \'.[] | select(.Names != null) | .Names[0]\' | sed \'/---/d\' | sort'
    else:
        # unsupported manager
        return []

    imgs_names = sorted(cmd_with_output(cmd=cmd, verbose=verbose).splitlines())
    return imgs_names


def image_remove(manager: str, image_name: str, verbose: bool) -> None:
    cmd_output_to_terminal(cmd=f'{manager} rmi -f {image_name}', verbose=verbose)


def list_image_layers(manager: str, image_name: str, verbose: bool) -> None:
    cmd = f'echo "\n{manager} - {image_name}";{manager} inspect --format json {image_name} | yq -p=j .[0].RootFS.Layers'
    cmd_output_to_terminal(cmd=cmd, verbose=verbose)


def prune_buildx(manager: str, verbose: bool) -> None:
    cmd_output_to_terminal(cmd=f'{manager} system prune -af --volumes', verbose=verbose)


def prune_system(manager: str, verbose: bool) -> None:
    cmd_output_to_terminal(cmd=f'{manager} buildx prune -af', verbose=verbose)


_dbox_export = 'distrobox-export'


def distrobox_assemble(manager: str, name: str, verbose: bool) -> None:
    cmd_output_to_terminal(
        cmd=f'DBX_CONTAINER_ALWAYS_PULL=0 DBX_CONTAINER_MANAGER={manager} distrobox assemble create --replace --name {name}',  # noqa E501
        verbose=verbose
    )


@contextmanager
def patched_distrobox_copied() -> Generator[None]:
    try:
        shutil.copy2(f'../{_dbox_export}', _dbox_export)

        yield
    finally:
        # remove it
        os.unlink(_dbox_export)


@contextmanager
def patched_distrobox_export(verbose: bool) -> Generator[None]:
    try:
        # patch it

        # uri='https://raw.githubusercontent.com/89luca89/distrobox/refs/tags/1.8.1.2/distrobox-export'
        # curl -sO ${uri}
        cmd_output_to_terminal(cmd=f'cp -f $(which {_dbox_export}) .', verbose=verbose)
        cmd_output_to_terminal(cmd=f'patch {_dbox_export} {_dbox_export}-1.8.1.2.patch', verbose=verbose)

        yield
    finally:
        # remove it
        os.unlink(_dbox_export)
