import json
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Tuple

import requests
import polling2
import click
from dotenv import load_dotenv
from rich.console import Console


class CLIManager:
    def __init__(self, skip_validation: bool = False) -> None:
        load_dotenv('.env')
        self.requests_session = requests.Session()
        self.__env_path = Path(".env")
        self.__token = os.getenv("TOKEN")
        self.__token_expiry = None
        self._dashboard_mode: bool = False
        self._console = Console()
        self._dashboard_lines = 0
        endpoint_to_verify = os.getenv("URL")

        # Verify the URL is valid and correct (skip for config command)
        if not skip_validation:
            self.__verify_correct_environment(endpoint_to_verify)
        self.__endpoint = endpoint_to_verify


    @classmethod
    def __verify_correct_environment(cls, url: str | None) -> bool:
        if url is None:
            raise ValueError("Please enter URL in your .env file!")

        reg_ex_result = re.search("https://[a-z]+.barkoagent.com",str(url))
        return reg_ex_result is not None

    def configure(self, token: str | None = None, url: str | None = None) -> Dict[str, str]:
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
    def get_project_data(self, project_id: str) -> dict[str, int]:
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

        formatted_data: dict[str,int] = {
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
        click.echo(f'Polling brain status: {brain_state['ready']}')
        return bool(brain_state['ready'])

    def run_single_script(self, project_id: str, chat_id: str, generate_report: bool = False) -> Any:
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
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/run_script/{project_id}/{chat_id}', json={"generate_report": generate_report}, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def run_all_scripts(self, project_id: str, generate_report: bool = False, junit: bool = False) -> Any:
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
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/run_script?project_id={project_id}', json={"generate_report": True}, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        if junit:
            batch_report_id = data.get("batch_report_id")
            if not batch_report_id:
                time.sleep(2)
                reports_data = self.get_batch_test_reports_list(project_id, limit=1, offset=0)
                reports = reports_data.get("reports", [])
                if not reports:
                    raise RuntimeError("No batch reports found. The batch report may still be initializing.")
                batch_report_id = reports[0]["batch_report_id"]
            
            results, failure_detected, failure_error = self._poll_batch_executions(batch_report_id)
            self._print_summary(results)
            if failure_error:
                raise failure_error
            data["results"] = results
            data["failed"] = failure_detected
        
        return data

    def _poll_batch_executions(self, batch_report_id: str) -> Tuple[List[Dict[str, Any]], bool]:
        completed: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        failure_detected = False
        start_times: Dict[str, float] = {}
        end_times: Dict[str, float] = {}

        while True:
            response = self.get_batch_executions(batch_report_id, limit=200)
            execution_list = response.get("executions", [])

            all_complete = True
            for execution in execution_list:
                normalized = self._normalize_execution(execution)
                exec_id = normalized["id"]

                if exec_id not in start_times:
                    start_times[exec_id] = time.time()

                if not normalized["complete"]:
                    all_complete = False

                if exec_id not in seen_ids and normalized["complete"]:
                    seen_ids.add(exec_id)
                    end_times[exec_id] = time.time()
                    duration = max(0.0, end_times[exec_id] - start_times[exec_id])
                    normalized["time"] = duration
                    completed.append(normalized)
                    self._render_dashboard(completed)

                    if normalized["failed"]:
                        failure_detected = True

            if all_complete:
                self._render_dashboard(completed)
                break

            time.sleep(2)

        return completed, failure_detected

    def _normalize_execution(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        status_value = execution.get("status", "").lower()
        exec_id = execution.get("chat_id", "")
        name = execution.get("chat_title", exec_id)
        output = execution.get("output", "")

        return {
            "id": exec_id,
            "name": name,
            "status": status_value or "unknown",
            "failed": status_value == "failed",
            "complete": status_value in {"passed", "failed"},
            "output": output,
        }

    def _render_dashboard(self, results: List[Dict[str, Any]]):
        ordered = sorted(results, key=lambda r: (not r["failed"], r["name"]))
        failed = [r for r in ordered if r["failed"]]
        passed = [r for r in ordered if not r["failed"]]
        
        if self._dashboard_lines > 0:
            print(f"\x1b[{self._dashboard_lines}A", end="", flush=True)
        
        line_count = 0
        
        print("\x1b[2KTest Execution Status")
        line_count += 1
        
        print(f"\x1b[2KTotal: {len(ordered)}  Passed: \x1b[32m{len(passed)}\x1b[0m  Failed: \x1b[{'31' if failed else '32'}m{len(failed)}\x1b[0m")
        line_count += 1
        
        print("\x1b[2K")
        line_count += 1
        
        print("\x1b[2KFAILED TESTS")
        line_count += 1
        if not failed:
            print("\x1b[2K  (none)")
            line_count += 1
        else:
            for r in failed:
                print("\x1b[2K  [", end="")
                self._console.print("FAILED", style="bold red", end="")
                print(f"] {r['name']} ({r['id']}) - {r.get('time', 0):.3f}s")
                line_count += 1
        
        print("\x1b[2K")
        line_count += 1
        
        print("\x1b[2KPASSED")
        line_count += 1
        if not passed:
            print("\x1b[2K  (none)")
            line_count += 1
        else:
            for r in passed:
                print("\x1b[2K  [", end="")
                self._console.print("PASSED", style="bold green", end="")
                print(f"] {r['name']} ({r['id']}) - {r.get('time', 0):.3f}s")
                line_count += 1
        
        self._dashboard_lines = line_count

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
