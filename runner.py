import click
from src.main import CLIManager



@click.group()
@click.option('--config', default='config.yml')
@click.pass_context
def cli(ctx, config):
    ctx.ensure_object(CLIManager)


@cli.command()
@click.pass_context
def login_local(ctx):
    cli_manager = ctx.obj
    temp = cli_manager.get_local_user_token()
    click.echo(f"login_local: {temp}")


@cli.command()
@click.option('--project-id', help='Get project data information')
@click.pass_context
def get_project_data(ctx, project_id):
    cli_manager = ctx.obj
    temp = cli_manager.get_project_data(project_id)
    click.echo(f"get_project_data: {temp}")

@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.option('--chat-id', help='project ID for running single script')
@click.pass_context
def run_single_script(ctx, project_id, chat_id):
    cli_manager = ctx.obj
    temp = cli_manager.run_single_script(project_id, chat_id)
    click.echo(f"run_single_script: {temp}")


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def run_all_scripts(ctx, project_id):
    cli_manager = ctx.obj
    temp = cli_manager.run_all_scripts(project_id)
    click.echo(f"run_all_scripts: {temp}")


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def get_all_results(ctx, project_id):
    cli_manager = ctx.obj
    temp = cli_manager.get_test_results(project_id)
    click.echo(f"get_all_results: {temp}")


@cli.command()
@click.pass_context
def exit_client(ctx):
    cli_manager = ctx.obj
    cli_manager.exit_client()
    ctx.obj = None
    click.echo(f"exit_client")


if __name__ == '__main__':
    cli()