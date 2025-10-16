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
    click.echo(pretty)

@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.option('--chat-id', help='project ID for running single script')
@click.pass_context
def run_single_script(ctx, project_id, chat_id):
    cli_manager = ctx.obj
    output = cli_manager.run_single_script(project_id, chat_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def run_all_scripts(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.run_all_scripts(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def get_all_results(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_test_results(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

# get_batch_test_reports_list
@cli.command()
@click.option('--project-id', help='project ID for getting the batch test reports list')
@click.pass_context
def get_batch_test_reports_list(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_batch_test_reports_list(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


# get_batch_report_details
@cli.command()
@click.option('--batch-report-id', help='batch report ID for getting the specific batch test report')
@click.pass_context
def get_batch_report_details(ctx, batch_report_id):
    cli_manager = ctx.obj
    output = cli_manager.get_batch_report_details(batch_report_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

# get_batch_executions
@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def get_all_results(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_test_results(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

# delete_batch_report
@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.pass_context
def get_all_results(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_test_results(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

@cli.command()
@click.pass_context
def exit_client(ctx):
    cli_manager = ctx.obj
    cli_manager.exit_client()
    ctx.obj = None


if __name__ == '__main__':
    cli()