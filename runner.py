import json

import click
from cli_manager import CLIManager

A11Y_POLICIES = ["after_navigation", "after_each_step", "selected_steps", "final_only"]

def _build_a11y_config(accessibility, a11y_policy, a11y_steps):
    if not accessibility:
        return None
    config = {"enabled": True, "policy": a11y_policy}
    if a11y_policy == "selected_steps":
        config["checkpoint_steps"] = [int(s.strip()) for s in a11y_steps.split(",")]
    return config

def _validate_a11y_flags(accessibility, a11y_policy, a11y_steps):
    if not accessibility and (a11y_policy != "after_navigation" or a11y_steps):
        raise click.UsageError("--a11y-policy and --a11y-steps require --accessibility to be set.")
    if accessibility and a11y_policy == "selected_steps" and not a11y_steps:
        raise click.UsageError("--a11y-steps is required when --a11y-policy is 'selected_steps'.")
    if a11y_steps and a11y_policy != "selected_steps":
        raise click.UsageError("--a11y-steps can only be used with --a11y-policy 'selected_steps'.")

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
    if ctx.invoked_subcommand != 'config':
        ctx.ensure_object(CLIManager)

@cli.command()
@click.option("--set-token", "token", help="set the auth token used by the CLI")
@click.option("--set-url", "url", help="set the BarkoAgent API URL")
def config(token, url):
    if token is None and url is None:
        raise click.UsageError("Provide --set-token, --set-url, or both.")
    cli_manager = CLIManager(skip_validation=True)
    updated = cli_manager.configure(token=token, url=url)
    click.echo(f"Configuration updated: URL={updated.get('URL','')}, TOKEN set={bool(updated.get('TOKEN'))}")

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
@click.option('--chat-id', help='chat ID for running single script')
@click.option('--junit', is_flag=True, help='generate junit xml report')
@click.option('--html', is_flag=True, help='generate html report')
@click.option('--environment-id', default=None, help='environment ID to use for this run')
@click.option('--accessibility', is_flag=True, help='enable accessibility auditing for this run')
@click.option('--a11y-policy', type=click.Choice(A11Y_POLICIES, case_sensitive=False), default='after_navigation', help='accessibility audit policy')
@click.option('--a11y-steps', type=str, default=None, help='comma-separated step numbers for selected_steps policy (e.g. "1,5,10")')
@click.pass_context
def run_single_script(ctx, project_id, chat_id, junit, html, environment_id, accessibility, a11y_policy, a11y_steps):
    _validate_a11y_flags(accessibility, a11y_policy, a11y_steps)
    a11y_config = _build_a11y_config(accessibility, a11y_policy, a11y_steps)
    cli_manager = ctx.obj
    output = cli_manager.run_single_script(project_id, chat_id, junit=junit, html=html, return_data=not junit, environment_id=environment_id, replay_accessibility_audit=a11y_config)
    if not junit:
        pretty = json.dumps(output, indent=2, ensure_ascii=False)
        click.echo(pretty)


@cli.command()
@click.option('--project-id', help='project ID for running single script')
@click.option('--junit', is_flag=True, help='generate junit xml report')
@click.option('--html', is_flag=True, help='generate html report')
@click.option('--parallel', type=int, default=1, help='parallelism level (1-4). Values > 1 require a paid plan.')
@click.option('--environment-id', default=None, help='environment ID to use for this run')
@click.pass_context
def run_all_scripts(ctx, project_id, junit, html, parallel, environment_id):
    cli_manager = ctx.obj

    if parallel < 1 or parallel > 4:
        raise click.UsageError("--parallel must be between 1 and 4")

    if parallel > 1:
        plan_type = cli_manager.get_user_plan_type()
        if plan_type == 'free':
            raise click.UsageError(
                "Parallel execution (--parallel > 1) is only available for paid plans. "
                "Please upgrade your plan to use this feature."
            )

    output = cli_manager.run_all_scripts(project_id, junit=junit, html=html, return_data=not junit, parallelism=parallel, environment_id=environment_id)
    if not junit:
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

@cli.command()
@click.option('--project-id', required=True, help='project ID for getting folders')
@click.pass_context
def get_folders(ctx, project_id):
    """Get all folders for a project"""
    cli_manager = ctx.obj
    output = cli_manager.get_folders(project_id)
    pretty = json.dumps(output, indent=2, ensure_ascii=False)
    click.echo(pretty)

@cli.command()
@click.option('--project-id', required=True, help='project ID for running folder scripts')
@click.option('--folder-id', required=True, help='folder ID to run all scripts from')
@click.option('--junit', is_flag=True, help='generate junit xml report')
@click.option('--html', is_flag=True, help='generate html report')
@click.option('--parallel', type=int, default=1, help='parallelism level (1-4). Values > 1 require a paid plan.')
@click.option('--environment-id', default=None, help='environment ID to use for this run')
@click.pass_context
def run_folder(ctx, project_id, folder_id, junit, html, parallel, environment_id):
    cli_manager = ctx.obj

    if parallel < 1 or parallel > 4:
        raise click.UsageError("--parallel must be between 1 and 4")

    if parallel > 1:
        plan_type = cli_manager.get_user_plan_type()
        if plan_type == 'free':
            raise click.UsageError(
                "Parallel execution (--parallel > 1) is only available for paid plans. "
                "Please upgrade your plan to use this feature."
            )

    output = cli_manager.run_folder(project_id, folder_id, junit=junit, html=html, return_data=not junit, parallelism=parallel, environment_id=environment_id)
    if not junit:
        pretty = json.dumps(output, indent=2, ensure_ascii=False)
        click.echo(pretty)

if __name__ == '__main__':
    cli()
