from rich import box, print
from rich.table import Table
from rich.text import Text

from ocisictl.models import ContainerImage


def print_containerimage_table(imgs: list[ContainerImage], desc: str) -> None:
    table = Table(title=f'{desc.title()}', title_justify='left', box=box.ROUNDED)

    table.add_column('Name', style='blue3')
    table.add_column('Path')
    table.add_column('Enabled', justify='center', style='bold dark_green')
    table.add_column('Manager')
    table.add_column('Distrobox', style='orange4')
    table.add_column('Assemble', justify='center', style='bold green1')

    for img in imgs:
        img_tag = f':{img.tag}' if img.tag else ''
        image_w_tag = f'{img.name}{img_tag}'
        image = Text(image_w_tag, style='bold') if img.enabled else image_w_tag
        enabled = ':heavy_check_mark:' if img.enabled else ''
        mgr_name = img.manager_name('docker')
        manager = Text(mgr_name, style='bold') if mgr_name != 'docker' else mgr_name
        distrobox = (
            Text(img.distrobox_name, style='bold')
            if img.enabled and img.assemble
            else img.distrobox_name
            if img.assemble
            else img.distrobox
        )
        assemble = ':heavy_check_mark:' if img.assemble else ''

        table.add_row(image, img.path, enabled, manager, distrobox, assemble)

    print(table)
