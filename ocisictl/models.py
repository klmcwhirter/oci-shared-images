import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pprint import pformat
from typing import Optional

from yaml import Loader, load_all


@dataclass
class ContainerImage:
    """A single image to be created and optionally a container"""

    name: str
    path: str
    enabled: bool
    tag: Optional[str] = None
    manager: Optional[str] = None
    distrobox: Optional[str] = None
    assemble: Optional[bool] = None

    @property
    def distrobox_name(self) -> str:
        return self.distrobox if self.distrobox else self.name

    @property
    def full_image_name(self) -> str:
        # prefix = 'localhost/' if self.manager == 'podman' else ''
        prefix = ''
        return f'{prefix}{self.name}:{self.tag}' if self.tag else f'{prefix}{self.name}'

    def manager_name(self, default: str) -> str:
        return self.manager if self.manager else default

    def __post_init__(self) -> None:
        self.tag = self.tag if self.tag else 'latest'
        self.assemble = self.assemble is True or self.name.endswith('-dx')


@dataclass
class AppConfig:
    """The application config"""

    images: list[ContainerImage]

    @property
    def containers_to_assemble(self) -> list[ContainerImage]:
        return [ci for ci in self.images if ci.assemble and ci.enabled]

    @property
    def images_enabled(self) -> list[ContainerImage]:
        return [ci for ci in self.images if ci.enabled]

    @property
    def images_not_assemble(self) -> list[ContainerImage]:
        return [ci for ci in self.images if ci.enabled and not ci.assemble]

    @property
    def managers(self) -> list[str]:
        return sorted(set(ci.manager for ci in self.images if ci.manager))

    @staticmethod
    def from_yaml(file_path: str) -> AppConfig:  # noqa F821
        with open(file_path) as y:
            yobjs: list = list(*load_all(y, Loader=Loader))
            images = [ContainerImage(**ci) for ci in yobjs]
            return AppConfig(images=images)


@dataclass
class AppContext:
    """The app operating context"""

    args: argparse.Namespace
    config: AppConfig

    def __post_init__(self) -> None:
        self._setup_logging()

    @property
    def dbx_container_manager(self) -> str:
        return os.getenv('DBX_CONTAINER_MANAGER', 'docker')

    @property
    def managers(self) -> list[str]:
        mgrs = self.config.managers

        if len(mgrs) == 0:
            mgrs = [self.dbx_container_manager]

        return mgrs

    @property
    def list_all(self) -> bool:
        return self.args.all

    @property
    def list_assemble(self) -> bool:
        return self.args.assemble

    @property
    def list_enabled(self) -> bool:
        return self.args.enabled

    @property
    def list_layers(self) -> bool:
        return self.args.layers

    @property
    def prune(self) -> bool:
        return self.args.prune

    @property
    def skip_clean(self) -> bool:
        return hasattr(self.args, 'skip_clean') and self.args.skip_clean

    @property
    def verb(self) -> str:
        return self.args.verb

    @property
    def verbose(self) -> bool:
        return self.args.verbose

    def _setup_logging(self) -> None:
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level, stream=sys.stdout, format='{asctime} - {module} - {levelname} - {funcName} - {message}', style='{'
        )

    def log(self) -> None:
        logging.debug(pformat(self, indent=0, depth=3, width=196, compact=True, sort_dicts=False))

    @staticmethod
    def from_args(args: argparse.Namespace) -> AppContext:  # noqa F821
        app_config = AppConfig.from_yaml(args.file)
        return AppContext(args=args, config=app_config)
