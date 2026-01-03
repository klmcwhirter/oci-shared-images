"""Adapter classes and functions used by steps"""


from pathlib import Path
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
        idkey = '.[].Id'

    return cmd_with_output(cmd=f'{manager} ps --format json | yq -p=j {idkey} | sed "/---/d"', verbose=verbose).splitlines()


def image_build(manager: str, container_file: str, image_name: str, build_args: str, verbose: bool) -> None:
    cmd_output_to_terminal(
        cmd=f'{_CM_OPTS}{manager} buildx build -f {container_file} -t {image_name} {build_args} .', verbose=verbose
    )


def image_names(manager: str, verbose: bool) -> list[str]:
    cmd = ''
    if manager == 'docker':
        cmd = f'{manager} image ls --format json | yq -p=j \'select(.Repository != "<none>") | (.Repository + ":" + .Tag)\' | sed \'/---/d;/^:$/d\' | sort'  # noqa E501
    elif manager == 'podman':
        cmd = f'{manager} image ls --format json | yq -p=j ".[] | select(.Names != null) | .Names[0]" | sed "/---/d" | sort'
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
    cmd_output_to_terminal(cmd=f'{manager} buildx prune -af', verbose=verbose)


def prune_system(manager: str, verbose: bool) -> None:
    cm_opts = '--build' if manager == 'podman' else ''
    cmd_output_to_terminal(cmd=f'{manager} system prune -af --volumes {cm_opts}', verbose=verbose)


def distrobox_assemble(manager: str, name: str, verbose: bool) -> None:
    cmd_output_to_terminal(
        cmd=f'DBX_CONTAINER_ALWAYS_PULL=0 DBX_CONTAINER_MANAGER={manager} distrobox assemble create --replace --name {name}',
        verbose=verbose,
    )


def distrobox_assemble_fixup_bin(manager: str, bin: str) -> None:
    pbin = Path(bin)
    if text := pbin.read_text():
        lines_with_cm: list[str] = []
        lines = text.splitlines()

        for line in lines:
            if 'distrobox-enter' in line and 'DBX_CONTAINER_MANAGER=' not in line:
                line = f'\tDBX_CONTAINER_MANAGER={manager} {line.strip()}'

            lines_with_cm.append(line)

        text = '\n'.join(lines_with_cm)
        pbin.write_text(text)


def distrobox_assemble_fixup_bins(manager: str, name: str, verbose: bool) -> None:
    for bin in distrobox_export_bins_list(manager=manager, name=name, verbose=verbose):
        print(f'{bin}: {manager} {name}')
        distrobox_assemble_fixup_bin(manager=manager, bin=bin)


def distrobox_export_bins_list(manager: str, name: str, verbose: bool) -> list[str]:
    out = cmd_with_output(
        cmd=f'DBX_CONTAINER_ALWAYS_PULL=0 DBX_CONTAINER_MANAGER={manager} distrobox enter {name} -- distrobox-export --list-binaries',
        verbose=verbose,
    )
    lines = out.splitlines()
    bins = [
        line.partition('|')[2].strip()
        for line in lines
    ]
    return bins
