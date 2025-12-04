import json

import click
from cli_manager import CLIManager

class JSONListOfDicts(click.ParamType):
    name = "json_list_of_dicts"
    def convert(self, value, param, ctx):
        # value could be a string or an already-loaded Python object
        if isinstance(value, (list, tuple)):
            data = value
        else:
            try:
                data = json.loads(value)
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON: {e}", param, ctx)
        if not isinstance(data, list):
            self.fail("Value must be a JSON list", param, ctx)
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                self.fail(f"Item {i} is not an object", param, ctx)
            if "chat_id" not in item or "task_id" not in item:
                self.fail(f"Item {i} must contain 'chat_id' and 'task_id'", param, ctx)
        return data

JSON_LIST = JSONListOfDicts()

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
@click.option('--report', help='project ID for running single script', type=bool)
@click.pass_context
def run_single_script(ctx, project_id, chat_id, report):
    cli_manager = ctx.obj
    output = cli_manager.run_single_script(project_id, chat_id, report)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.option('--report', help='project ID for running single script', type=bool)
@click.pass_context
def run_all_scripts(ctx, project_id, report):
    cli_manager = ctx.obj
    output = cli_manager.run_all_scripts(project_id, report)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.option("--payload", type=JSON_LIST, help="JSON list string")
@click.option("--payload-file", type=click.File("r"), help="File with JSON list")
@click.pass_context
def get_all_results(ctx, project_id, payload, payload_file):
    cli_manager = ctx.obj
    if payload_file is not None:
        payload = JSON_LIST.convert(payload_file.read(), param=None, ctx=None)
    if payload is None:
        raise click.UsageError("Provide --payload or --payload-file")
    click.echo(f"Got {len(payload)} items")


    output = cli_manager.get_test_results(project_id, payload)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

@cli.command()
@click.option('--project-id', help='project ID for getting the batch test reports list')
@click.pass_context
def get_batch_test_reports_list(ctx, project_id):
    cli_manager = ctx.obj
    output = cli_manager.get_batch_test_reports_list(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


@cli.command()
@click.option('--batch-report-id', help='batch report ID for getting the specific batch test report')
@click.pass_context
def get_batch_report_details(ctx, batch_report_id):
    cli_manager = ctx.obj
    output = cli_manager.get_batch_report_details(batch_report_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

@cli.command()
@click.option('--batch-report-id', help='Batch report ID for getting batch executions')
@click.pass_context
def get_batch_executions(ctx, batch_report_id):
    cli_manager = ctx.obj
    output = cli_manager.get_batch_executions(batch_report_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

@cli.command()
@click.option('--batch-report-id', help='Batch report ID for deleting batch executions')
@click.pass_context
def delete_batch_report(ctx, batch_report_id):
    cli_manager = ctx.obj
    output = cli_manager.delete_batch_report(batch_report_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)


if __name__ == '__main__':
    cli()