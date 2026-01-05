import json
import os
from pathlib import Path
import re
import time
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
import polling2
import click
from dotenv import load_dotenv
from rich.console import Console
from utils.report_paths import ReportPathManager
from utils.junit_xml import generate_junit_xml


class CLIManager:
    def __init__(self, skip_validation: bool = False) -> None:
        load_dotenv('.env')
        self.requests_session = requests.Session()
        self.__env_path = Path(".env")
        self.__token = os.getenv("TOKEN")
        self.__token_expiry = None
        self._dashboard_mode: bool = False
        self._console = Console(highlight=False)
        self._dashboard_lines = 0
        endpoint_to_verify = os.getenv("URL")

        # Verify the URL is valid and correct (skip for config command)
        if not skip_validation:
            self.__verify_correct_environment(endpoint_to_verify)
        self.__endpoint = endpoint_to_verify


    @classmethod
    def __verify_correct_environment(cls, url: Optional[str]) -> bool:
        if url is None:
            raise ValueError("Please enter URL in your .env file!")

        reg_ex_result = re.search("https://[a-z]+.barkoagent.com",str(url))
        return reg_ex_result is not None

    def configure(self, token: Optional[str] = None, url: Optional[str] = None) -> Dict[str, str]:
        current: Dict[str, str] = {}
        if self.__env_path.exists():
            for line in self.__env_path.read_text().splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    current[key.strip()] = value.strip()

        if url is not None:
            current["URL"] = url
        if token is not None:
            current["TOKEN"] = token

        lines = [f"URL={current.get('URL', '')}", f"TOKEN={current.get('TOKEN', '')}"]
        self.__env_path.write_text("\n".join(lines))
        self.__endpoint = current.get("URL")
        self.__token = current.get("TOKEN")
        return current
    def get_project_data(self, project_id: str) -> Dict[str, int]:
        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.get(f'{self.__endpoint}/api/general/get-data/{project_id}', headers=headers, timeout=10)
        res.raise_for_status()
        raw_data = res.json()
        # Clean out the data for output
        project_info = raw_data[1][0]
        project_info.pop('idx')

        chats_info = raw_data[2]
        chat_entries_info = raw_data[4]

        formatted_data: Dict[str, int] = {
            'chats_size': len(chats_info),
            'chat_entries_size': len(chat_entries_info)
        }
        formatted_data = formatted_data | project_info
        return formatted_data

    def get_brain_status(self, project_id: str) -> bool:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(f'{self.__endpoint}/api/chats/brain_status?project_id={project_id}', headers=headers, timeout=10)
        res.raise_for_status()
        brain_state = res.json()
        return bool(brain_state['ready'])

    def get_user_profile(self) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.get(f'{self.__endpoint}/api/users/profile', headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_user_plan_type(self) -> str:
        try:
            profile = self.get_user_profile()
            return profile.get('usage', {}).get('plan', {}).get('type', 'free')
        except Exception:
            return 'free'

    def run_single_script(self, project_id: str, chat_id: str, junit: bool = False, html: bool = False, return_data: bool = True) -> Any:
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        self._dashboard_mode = junit
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/run_script/{project_id}/{chat_id}', json={"generate_report": True}, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        batch_report_id = None
        
        if junit or html:
            batch_report_id = data.get("batch_report_id")
            if not batch_report_id:
                time.sleep(2)
                reports_data = self.get_batch_test_reports_list(project_id, limit=1, offset=0)
                reports = reports_data.get("reports", [])
                if not reports:
                    raise RuntimeError("No batch reports found. The batch report may still be initializing.")
                batch_report_id = reports[0]["batch_report_id"]
        
        test_title = None
        if junit:
            results, failure_detected, failure_error = self._poll_batch_executions(batch_report_id, html=html, project_id=project_id, chat_id=chat_id, is_single=True)
            if failure_error:
                raise failure_error
            
            data["results"] = results
            data["failed"] = failure_detected
            
            if batch_report_id:
                executions_response = self.get_batch_executions(batch_report_id, limit=1, offset=0)
                executions = executions_response.get('executions', [])
                if executions:
                    test_title = executions[0].get('title', executions[0].get('chat_title', None))
            
            self._generate_junit_xml_report(
                results=results,
                project_id=project_id,
                batch_report_id=batch_report_id,
                report_type="single",
                test_title=test_title
            )
        
        if html and batch_report_id:
            if not test_title and batch_report_id:
                executions_response = self.get_batch_executions(batch_report_id, limit=1, offset=0)
                executions = executions_response.get('executions', [])
                if executions:
                    test_title = executions[0].get('title', executions[0].get('chat_title', None))
            
            self._generate_html_report(
                project_id, 
                batch_report_id, 
                is_single=True, 
                report_type="single",
                test_title=test_title
            )
        
        if not junit and not html:
            batch_report_id = data.get("batch_report_id")
            if batch_report_id:
                self._wait_for_batch_completion(batch_report_id)
        
        if return_data:
            return data

    def run_all_scripts(self, project_id: str, generate_report: bool = None, junit: bool = False, html: bool = False, return_data: bool = True, parallelism: int = 1) -> Any:
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        self._dashboard_mode = junit
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/run_script?project_id={project_id}', json={"generate_report": True, "parallelism": parallelism}, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        batch_report_id = None
        
        if junit or html:
            batch_report_id = data.get("batch_report_id")
            if not batch_report_id:
                time.sleep(2)
                reports_data = self.get_batch_test_reports_list(project_id, limit=1, offset=0)
                reports = reports_data.get("reports", [])
                if not reports:
                    raise RuntimeError("No batch reports found. The batch report may still be initializing.")
                batch_report_id = reports[0]["batch_report_id"]
        
        if junit:
            results, failure_detected, failure_error = self._poll_batch_executions(batch_report_id, html=html, project_id=project_id)
            if failure_error:
                raise failure_error
            
            data["results"] = results
            data["failed"] = failure_detected
            
            self._generate_junit_xml_report(
                results=results,
                project_id=project_id,
                batch_report_id=batch_report_id,
                report_type="all"
            )
        
        if html and batch_report_id:
            self._generate_html_report(
                project_id, 
                batch_report_id, 
                is_single=False,
                report_type="all"
            )
        
        if not junit and not html:
            batch_report_id = data.get("batch_report_id")
            if batch_report_id:
                self._wait_for_batch_completion(batch_report_id)
        
        if return_data:
            return data

    def _wait_for_batch_completion(self, batch_report_id: str) -> None:
        while True:
            batch_report = self.get_batch_report_details(batch_report_id)
            batch_status = batch_report.get("status", "").lower()
            if batch_status in {"completed", "failed", "partial_failed"}:
                break
            time.sleep(2)

    def _build_dashboard_text(self, results: List[Dict[str, Any]], pending: List[Dict[str, Any]] = []) -> str:
        from rich.markup import escape
        ordered = sorted(results, key=lambda r: (not r["failed"], r["name"]))
        failed = [r for r in ordered if r["failed"]]
        passed = [r for r in ordered if not r["failed"]]
        total = len(ordered) + len(pending)
        
        lines = []
        lines.append(f"Total: {total}  Passed: [green]{len(passed)}[/green]  Failed: [red]{len(failed)}[/red]  Pending: [yellow]{len(pending)}[/yellow]")
        lines.append("")
        lines.append("[bold]FAILED TESTS[/bold]")
        if not failed:
            lines.append("  (none)")
        else:
            for r in failed:
                name = escape(r['name'])
                lines.append(f"  [[bold red]FAILED[/bold red]] {name} ({r['id']}) - {r.get('time', 0):.3f}s")
        lines.append("")
        lines.append("[bold]PASSED TESTS[/bold]")
        if not passed:
            lines.append("  (none)")
        else:
            for r in passed:
                name = escape(r['name'])
                lines.append(f"  [[bold green]PASSED[/bold green]] {name} ({r['id']}) - {r.get('time', 0):.3f}s")
        lines.append("")
        lines.append("[bold]PENDING TESTS[/bold]")
        if not pending:
            lines.append("  (none)")
        else:
            for r in pending:
                name = escape(r['name'])
                lines.append(f"  [[bold yellow]PENDING[/bold yellow]] {name} ({r['id']})")
        
        return "\n".join(lines)

    def _poll_batch_executions(self, batch_report_id: str, html: bool = False, project_id: str = None, chat_id: str = None, is_single: bool = False) -> Tuple[List[Dict[str, Any]], bool, Any]:
        from rich.live import Live
        from rich.markup import escape
        
        completed: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()
        failure_detected = False
        start_times: Dict[str, float] = {}
        end_times: Dict[str, float] = {}

        with Live(self._build_dashboard_text([], []), refresh_per_second=4, console=self._console) as live:
            while True:
                batch_report = self.get_batch_report_details(batch_report_id)
                batch_status = batch_report.get("status", "").lower()
                
                response = self.get_batch_executions(batch_report_id, limit=200)
                execution_list = response.get("executions", [])
                
                if not execution_list:
                    break
                
                all_tests = []
                for execution in execution_list:
                    normalized = self._normalize_execution(execution)
                    
                    if chat_id and normalized["id"] != chat_id:
                        continue
                        
                    all_tests.append(normalized)
                
                for test in all_tests:
                    exec_id = test["id"]

                    if exec_id not in start_times:
                        start_times[exec_id] = time.time()

                    if exec_id not in seen_ids and test["complete"]:
                        seen_ids.add(exec_id)
                        end_times[exec_id] = time.time()
                        
                        if test.get("api_duration") is not None:
                            duration = float(test["api_duration"])
                        else:
                            duration = max(0.0, end_times[exec_id] - start_times[exec_id])
                        
                        test["time"] = duration
                        completed.append(test)

                        if test["failed"]:
                            failure_detected = True
                
                pending = [t for t in all_tests if t["id"] not in seen_ids and not t["complete"]]
                
                live.update(self._build_dashboard_text(completed, pending))

                if batch_status in {"completed", "failed", "partial_failed"}:
                    break

                time.sleep(2)

        if is_single:
            print(f"\n\x1b[1mTest executed!\x1b[0m")
        else:
            print(f"\n\x1b[1mAll tests executed!\x1b[0m")

        return completed, failure_detected, None

    def _normalize_execution(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        status_value = execution.get("status", "").lower()
        exec_id = execution.get("chat_id", "")
        name = execution.get("chat_title", exec_id)
        output = execution.get("output", "")
        duration = execution.get("duration_seconds")

        return {
            "id": exec_id,
            "name": name,
            "status": status_value or "unknown",
            "failed": status_value == "failed",
            "complete": status_value in {"passed", "failed"},
            "output": output,
            "api_duration": duration,
        }

    def get_test_results(self, project_id: str, payload: list) -> Any:
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.post(f'{self.__endpoint}/api/chats/script_results?project_id={project_id}', json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def get_batch_test_reports_list(self, project_id:str, limit: int=20, offset: int=0) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(f'{self.__endpoint}/api/chats/project_reports/{project_id}?limit={limit}&offet={offset}',headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def get_batch_report_details(self, batch_report_id: str) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(
            f'{self.__endpoint}/api/chats/batch_report/{batch_report_id}', headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def get_batch_executions(self, batch_report_id: str, limit: int=20, offset: int=0) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(
            f'{self.__endpoint}/api/chats/batch_report/{batch_report_id}/executions?limit={limit}&offet={offset}', headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def delete_batch_report(self, batch_report_id: str) -> Any:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.delete(
            f'{self.__endpoint}/api/chats/batch_report/{batch_report_id}', headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def _generate_html_report(
        self, 
        project_id: str, 
        batch_report_id: str, 
        is_single: bool = False,
        report_type: str = "all",
        test_title: str = None,
        folder_name: str = None
    ) -> None:
        try:
            batch_report = self.get_batch_report_details(batch_report_id)
            
            executions_response = self.get_batch_executions(batch_report_id, limit=200, offset=0)
            executions = executions_response.get('executions', [])
            
            try:
                project_data = self.get_project_data(project_id)
                project_name = project_data.get('name', f'Project_{project_id}')
            except Exception as e:
                project_name = f"Project_{project_id}"
            
            report_data = {
                'reports': [batch_report],
                'executions': executions,
                'projectName': project_name
            }
            
            template_path = Path(__file__).parent / 'utils' / 'report_template.js'
            
            if not template_path.exists():
                click.echo(f"Warning: Report template not found at {template_path}")
                click.echo("HTML report generation skipped.")
                return
            
            path_manager = ReportPathManager()
            template_function = 'generateAllReportsHTML'
            
            if report_type == "single":
                if not test_title and executions:
                    test_title = executions[0].get('title', executions[0].get('chat_title', 'test'))
                output_filename = path_manager.get_single_report_path(project_name, test_title or 'test', batch_report_id)
            elif report_type == "folder":
                output_filename = path_manager.get_folder_report_path(project_name, folder_name or 'folder', batch_report_id)
            else:
                output_filename = path_manager.get_all_reports_path(project_name, batch_report_id)
            node_script = f'''
const {{ {template_function} }} = require('{template_path.as_posix()}');
const fs = require('fs');

const data = {json.dumps(report_data)};
const html = {template_function}(data.reports, data.executions, data.projectName);

fs.writeFileSync('{output_filename.as_posix()}', html, 'utf-8');
console.log('HTML report generated: {output_filename}');
'''
            output_filename.parent.mkdir(parents=True, exist_ok=True)
            temp_script_path = Path('temp_generate_html.js')
            temp_script_path.write_text(node_script)
            
            result = subprocess.run(
                ['node', str(temp_script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            temp_script_path.unlink()
            
            if result.returncode == 0:
                print(f"\x1b[1mHTML report generated: {output_filename}\x1b[0m")
            else:
                click.echo(f"Error generating HTML report: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            click.echo("Error: HTML generation timed out")
        except Exception as e:
            click.echo(f"Error generating HTML report: {str(e)}")

    def _generate_junit_xml_report(
        self,
        results: List[Dict[str, Any]],
        project_id: str,
        batch_report_id: str,
        report_type: str = "all",
        test_title: str = None,
        folder_name: str = None
    ) -> None:
        """
        Generate a JUnit XML report from test results.
        
        Args:
            results: List of test result dictionaries
            project_id: The project ID
            batch_report_id: The batch report ID
            report_type: Type of report - "single", "folder", or "all"
            test_title: Title for single test reports
            folder_name: Name for folder reports
        """
        try:
            try:
                project_data = self.get_project_data(project_id)
                project_name = project_data.get('name', f'Project_{project_id}')
            except Exception:
                project_name = f"Project_{project_id}"
            
            xml_content = generate_junit_xml(
                results=results,
                project_name=project_name,
                batch_report_id=batch_report_id
            )
            
            path_manager = ReportPathManager()
            
            if report_type == "single":
                output_path = path_manager.get_single_xml_path(
                    project_name, 
                    test_title or 'test', 
                    batch_report_id
                )
            elif report_type == "folder":
                output_path = path_manager.get_folder_xml_path(
                    project_name, 
                    folder_name or 'folder', 
                    batch_report_id
                )
            else:
                output_path = path_manager.get_all_reports_xml_path(
                    project_name, 
                    batch_report_id
                )
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(xml_content, encoding='utf-8')
            
            print(f"\x1b[1mJUnit XML report generated: {output_path}\x1b[0m")
            
        except Exception as e:
            click.echo(f"Error generating JUnit XML report: {str(e)}")

    def get_folders(self, project_id: str) -> List[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.get(
            f'{self.__endpoint}/api/folders/{project_id}',
            headers=headers,
            timeout=30
        )
        res.raise_for_status()
        return res.json()

    def run_folder(self, project_id: str, folder_id: str, junit: bool = False, html: bool = False, return_data: bool = True, parallelism: int = 1) -> Any:
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        self._dashboard_mode = junit
        
        folder_name = None
        if html:
            try:
                folders_data = self.get_folders(project_id)
                for folder in folders_data:
                    if folder.get('id') == folder_id or folder.get('_id') == folder_id:
                        folder_name = folder.get('name', folder.get('title', 'folder'))
                        break
            except Exception:
                folder_name = 'folder'
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        
        res = self.requests_session.post(
            f'{self.__endpoint}/api/chats/run_folder/{project_id}/{folder_id}',
            json={"generate_report": True, "parallelism": parallelism},
            headers=headers,
            timeout=10
        )
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                error_detail = res.json()
                raise RuntimeError(f"Server error: {error_detail}") from e
            except:
                raise RuntimeError(f"Server error: {res.text}") from e
        data = res.json()
        
        batch_report_id = None
        
        if junit or html:
            batch_report_id = data.get("batch_report_id")
            if not batch_report_id:
                time.sleep(2)
                reports_data = self.get_batch_test_reports_list(project_id, limit=1, offset=0)
                reports = reports_data.get("reports", [])
                if not reports:
                    raise RuntimeError("No batch reports found. The batch report may still be initializing.")
                batch_report_id = reports[0]["batch_report_id"]
        
        if junit:
            results, failure_detected, failure_error = self._poll_batch_executions(
                batch_report_id,
                html=html,
                project_id=project_id
            )
            if failure_error:
                raise failure_error
            
            data["results"] = results
            data["failed"] = failure_detected
            
            self._generate_junit_xml_report(
                results=results,
                project_id=project_id,
                batch_report_id=batch_report_id,
                report_type="folder",
                folder_name=folder_name
            )
        
        if html and batch_report_id:
            is_single = len(data.get("submitted_tasks", {})) == 1
            self._generate_html_report(
                project_id, 
                batch_report_id, 
                is_single=is_single,
                report_type="folder",
                folder_name=folder_name
            )
        
        # If no report flags, wait for batch to complete before returning
        if not junit and not html:
            batch_report_id = data.get("batch_report_id")
            if batch_report_id:
                self._wait_for_batch_completion(batch_report_id)
        
        if return_data:
            return data

