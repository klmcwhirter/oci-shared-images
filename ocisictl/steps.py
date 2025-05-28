import logging
import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from pprint import pformat
from typing import Generator

from ocisictl.models import AppContext, ContainerImage
from ocisictl.utils import (cmd_output_to_terminal, cmd_with_output,
                            log_entry_exit)


def assemble_distrobox(ctx: AppContext, image: ContainerImage) -> None:
    logging.info(f'Assembling {image.distrobox_name} using {image.manager} ...')

    cmd_output_to_terminal(
        cmd=f'DBX_CONTAINER_ALWAYS_PULL=0 DBX_CONTAINER_MANAGER={image.manager} distrobox assemble create --replace --name {image.distrobox_name}',  # noqa E501
        ctx=ctx,
        verbose=ctx.verbose
    )

    logging.info(f'Assembling {image.distrobox_name} using {image.manager} ... done.')


@contextmanager
def changed_dir(path: str) -> Generator[None]:
    origin = Path().absolute()
    logging.info(f'{origin=} ==> {path=}')

    try:
        os.chdir(path)

        yield
    finally:
        os.chdir(origin)


@log_entry_exit
def clean_images(ctx: AppContext) -> None:
    if not ctx.skip_clean:
        for img in reversed(ctx.config.images_not_assemble):
            logging.info(f'Cleaning {img.full_image_name} with {img.manager} ...')

            cmd_output_to_terminal(cmd=f'{img.manager} rmi -f {img.full_image_name}', ctx=ctx, verbose=ctx.verbose)

            logging.info(f'Cleaning {img.full_image_name} with {img.manager} ... done.')

        for manager in ctx.managers:
            cmd_output_to_terminal(cmd=f'{manager} buildx prune -af', ctx=ctx, verbose=ctx.verbose)
    else:
        logging.warning(f'Skipping clean images - skip-clean={ctx.skip_clean}')


def create_image(ctx: AppContext, image: ContainerImage) -> None:
    logging.info(f'Creating {image.full_image_name} using {image.manager} ...')

    if not ctx.prune:
        cmd_output_to_terminal(cmd=f'{image.manager} stop {image.distrobox_name}', ctx=ctx, verbose=ctx.verbose)
        # cmd_output_to_terminal(cmd=f'{image.manager} rm -f --volumes {image.distrobox_name}', ctx=ctx, verbose=ctx.verbose)
        # cmd_output_to_terminal(cmd=f'{image.manager} rmi -f {image.full_image_name}', ctx=ctx, verbose=ctx.verbose)

    build_args = ''
    cf_suffix = image.name
    name = image.name
    if name.endswith('-dx'):
        build_args = '--build-arg USER=$USER'
        build_args += ' --build-arg UID=`id -u $USER`'
        build_args += ' --build-arg GID=`id -g $USER`'

        if image.manager == 'podman':
            name = f'localhost/{name}'

        build_args += f' --build-arg IMG={name.removesuffix("-dx")}'

        build_args += f' --build-arg TAG={image.tag}'
        cf_suffix = "img-dx"

    # CM_OPTS = 'BUILDKIT_PROGRESS=plain '
    CM_OPTS = ''
    with changed_dir(image.path):
        with patched_distrobox_copied(ctx):
            cmd_output_to_terminal(
                cmd=f'{CM_OPTS}{image.manager} buildx build -f Containerfile.{cf_suffix} -t {image.full_image_name} {build_args} .',
                ctx=ctx,
                verbose=ctx.verbose
            )

    logging.info(f'Creating {image.full_image_name} using {image.manager} ... done.')


def containers_running(manager: str, ctx: AppContext) -> list[str]:
    idkey = '.ID'

    if manager == 'podman':
        idkey = ".[].Id"

    return cmd_with_output(
        cmd=f'{manager} ps --format json | yq -p=j {idkey} | sed \'/---/d\'',
        ctx=ctx,
        verbose=ctx.verbose
    ).splitlines()


@log_entry_exit
def do_prune(ctx: AppContext) -> None:
    for manager in ctx.managers:
        logging.info(f'Shutting down and pruning using {manager} ...')

        for c in containers_running(manager=manager, ctx=ctx):
            cmd_output_to_terminal(cmd=f'{manager} stop {c}', ctx=ctx, verbose=ctx.verbose)

        cmd_output_to_terminal(cmd=f'{manager} system prune -af --volumes', ctx=ctx, verbose=ctx.verbose)
        cmd_output_to_terminal(cmd=f'{manager} buildx prune -af', ctx=ctx, verbose=ctx.verbose)

        logging.info(f'Shutting down and pruning using {manager} ... done.')


@log_entry_exit
def list_assemble(ctx: AppContext) -> None:
    '''Given the config file in force, list the containers to assemble'''
    print(pformat(ctx.config.containers_to_assemble, width=196, compact=True, sort_dicts=False))


@log_entry_exit
def list_enabled(ctx: AppContext) -> None:
    '''Given the config file in force, list the images to create'''
    print(pformat(ctx.config.images_enabled, width=196, compact=True, sort_dicts=False))


@log_entry_exit
def list_layers(ctx: AppContext) -> None:
    for manager in ctx.config.managers:
        cmd = ''
        if manager == 'docker':
            cmd = f'{manager} image ls --format json | yq -p=j \'select(.Repository != "<none>") | (.Repository + ":" + .Tag)\' | sed \'/---/d;/^:$/d\' | sort'  # noqa E501
        elif manager == 'podman':
            cmd = f'{manager} image ls --format json | yq -p=j \'.[] | select(.Names != null) | .Names[0]\' | sed \'/---/d\' | sort'
        else:
            continue

        imgs_names = sorted(cmd_with_output(cmd=cmd, ctx=ctx, verbose=ctx.verbose).splitlines())
        logging.debug(pformat(imgs_names))

        for img_name in imgs_names:
            logging.debug(f'{manager} - {img_name}')
            cmd = f'echo "\n{manager} - {img_name}";{manager} inspect --format json {img_name} | yq -p=j .[0].RootFS.Layers'
            cmd_output_to_terminal(cmd=cmd, ctx=ctx, verbose=ctx.verbose)


@contextmanager
def patched_distrobox_copied(ctx: AppContext) -> Generator[None]:
    try:
        shutil.copy2('../distrobox-export', 'distrobox-export')

        yield
    finally:
        # remove it
        os.unlink('distrobox-export')


@log_entry_exit
@contextmanager
def patched_distrobox_export(ctx: AppContext) -> Generator[None]:
    try:
        # patch it

        # uri='https://raw.githubusercontent.com/89luca89/distrobox/refs/tags/1.8.1.2/distrobox-export'
        # curl -sO ${uri}
        cmd_output_to_terminal(cmd='cp -f $(which distrobox-export) .', ctx=ctx, verbose=ctx.verbose)
        cmd_output_to_terminal(cmd='patch distrobox-export distrobox-export-1.8.1.2.patch', ctx=ctx, verbose=ctx.verbose)

        yield
    finally:
        # remove it
        os.unlink('distrobox-export')


@log_entry_exit
def process(ctx: AppContext) -> None:
    if ctx.prune:
        do_prune(ctx=ctx)

    with patched_distrobox_export(ctx=ctx):
        for img in ctx.config.images_enabled:
            create_image(ctx=ctx, image=img)

    logging.info('allow system to coallesce')
    time.sleep(5)

    for img in ctx.config.containers_to_assemble:
        assemble_distrobox(ctx=ctx, image=img)

    clean_images(ctx=ctx)


def run_steps(ctx: AppContext) -> None:
    if ctx.verb == 'list':
        if ctx.list_layers:
            list_layers(ctx=ctx)
        elif ctx.list_assemble:
            list_assemble(ctx=ctx)
        elif ctx.list_enabled:
            list_enabled(ctx=ctx)
    elif ctx.verb == 'clean':
        clean_images(ctx=ctx)
    else:
        process(ctx=ctx)
