import json

import click
from cli_manager import CLIManager

@click.group()
@click.option('--config', default='config.yml')
@click.pass_context
def cli(ctx, config):
    ctx.ensure_object(CLIManager)

@cli.command()
@click.pass_context
def login_local(ctx):
    cli_manager = ctx.obj
    output = cli_manager.get_local_user_token()
    click.echo(f"User: email - {output['userEmail']},  username - {output['userName']}, message - {output['message']}")


@cli.command()
@click.option('--project-id', help='Get project data information')
@click.pass_context
def get_project_data(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_project_data(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo("get_project_data")
    click.echo(pretty)

@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.option('--chat-id', help='project ID for running single script')
@click.pass_context
def run_single_script(ctx, project_id, chat_id):
    cli_manager = ctx.obj
    output = cli_manager.run_single_script(project_id, chat_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo("run_single_script")
    click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def run_all_scripts(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.run_all_scripts(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo("run_all_scripts")
    click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def get_all_results(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_test_results(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo("get_all_results")
    click.echo(pretty)


@cli.command()
@click.pass_context
def exit_client(ctx):
    cli_manager = ctx.obj
    cli_manager.exit_client()
    ctx.obj = None
    click.echo(f"exit_client")


if __name__ == '__main__':
    cli()