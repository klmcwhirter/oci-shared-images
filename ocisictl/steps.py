import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from pprint import pformat
from typing import Generator

from ocisictl.adapters import (
    container_remove,
    container_stop,
    containers_running,
    distrobox_assemble,
    image_build,
    image_names,
    image_remove,
    list_image_layers,
    patched_distrobox_copied,
    patched_distrobox_export,
    prune_buildx,
    prune_system
)
from ocisictl.models import AppContext, ContainerImage
from ocisictl.utils import log_entry_exit


def assemble_distrobox(ctx: AppContext, image: ContainerImage) -> None:
    manager = image.manager_name(default=ctx.dbx_container_manager)

    logging.info(f'Assembling {image.distrobox_name} using {manager} ...')

    distrobox_assemble(manager=manager, name=image.distrobox_name, verbose=ctx.verbose)

    logging.info(f'Assembling {image.distrobox_name} using {manager} ... done.')


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
    for image in reversed(ctx.config.images_not_assemble):
        manager = image.manager_name(default=ctx.dbx_container_manager)

        logging.info(f'Cleaning {image.full_image_name} with {manager} ...')

        image_remove(manager=manager, image_name=image.full_image_name, verbose=ctx.verbose)

        logging.info(f'Cleaning {image.full_image_name} with {manager} ... done.')

    for manager in ctx.managers:
        logging.info(f'Pruning buildx with {manager}')
        prune_buildx(manager=manager, verbose=ctx.verbose)


def create_image(ctx: AppContext, image: ContainerImage) -> None:
    manager = image.manager_name(default=ctx.dbx_container_manager)

    logging.info(f'Creating {image.full_image_name} using {manager} ...')

    if not ctx.prune:
        container_stop(manager=manager, name=image.distrobox_name, verbose=ctx.verbose)
        container_remove(manager=manager, name=image.distrobox_name, verbose=ctx.verbose)
        image_remove(manager=manager, image_name=image.full_image_name, verbose=ctx.verbose)

    build_args = ''
    cf_suffix = image.name
    if image.name.endswith('-dx'):
        build_args = '--build-arg USER=$USER'
        build_args += ' --build-arg UID=`id -u $USER`'
        build_args += ' --build-arg GID=`id -g $USER`'

        build_args += f' --build-arg IMG={image.name.removesuffix("-dx")}'
        build_args += f' --build-arg TAG={image.tag}'

        cf_suffix = "img-dx"

    with changed_dir(image.path):
        with patched_distrobox_copied():
            image_build(
                manager=manager,
                container_file=f'Containerfile.{cf_suffix}',
                image_name=image.full_image_name,
                build_args=build_args,
                verbose=ctx.verbose)

    logging.info(f'Creating {image.full_image_name} using {manager} ... done.')


@log_entry_exit
def do_prune(ctx: AppContext) -> None:
    for manager in ctx.managers:
        logging.info(f'Shutting down and pruning using {manager} ...')

        for c in containers_running(manager=manager, verbose=ctx.verbose):
            container_stop(manager=manager, name=c, verbose=ctx.verbose)

        prune_buildx(manager=manager, verbose=ctx.verbose)
        prune_system(manager=manager, verbose=ctx.verbose)

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
        imgs_names = image_names(manager=manager, verbose=ctx.verbose)
        if len(imgs_names) == 0:
            continue

        logging.debug(pformat(imgs_names))

        for img_name in imgs_names:
            logging.debug(f'{manager} - {img_name}')
            list_image_layers(manager=manager, image_name=img_name, verbose=ctx.verbose)


@log_entry_exit
def process(ctx: AppContext) -> None:
    if ctx.prune:
        do_prune(ctx=ctx)

    with patched_distrobox_export(verbose=ctx.verbose):
        for img in ctx.config.images_enabled:
            create_image(ctx=ctx, image=img)

    logging.info('allow system to coallesce')
    time.sleep(5)

    for img in ctx.config.containers_to_assemble:
        assemble_distrobox(ctx=ctx, image=img)

    if not ctx.skip_clean:
        clean_images(ctx=ctx)
    else:
        logging.warning(f'Skipping clean images - skip-clean={ctx.skip_clean}')


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
