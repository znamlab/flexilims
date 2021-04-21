import click
import znamdb.main


@click.group()
def cli():
    pass


@cli.command()
@click.option('-p', '--project_id', prompt='Enter the project ID', help='Project ID.')
@click.option('-m', '--mouse_name', prompt='Enter the name of the mouse you want to add',
              help='Name of the mouse for flexilims.')
@click.option('--mcms_animal_name', default=None, help='Name of the mouse on MCMS (if different from mouse_name).')
@click.option('--flexilims_username', default=None, help='Your username on flexilims.')
@click.option('--mcms_username', default=None, help='Your username on mcms.')
def add_mouse(project_id, mouse_name, mcms_animal_name=None, flexilims_username=None, mcms_username=None):
    """Add a single mouse to a project."""
    click.echo('Trying to add %s in %s' % (mouse_name, project_id))
    znamdb.main.add_mouse(mouse_name, project_id, mcms_animal_name, flexilims_username, mcms_username)


if __name__ == '__main__':
    znamdb.main.add_mouse(mouse_name='PZAJ2.1c', project_id='virus_tests')
