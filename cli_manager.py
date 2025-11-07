import json
import os
from datetime import datetime
from pathlib import Path
import re

import requests
import polling2
import click
from dotenv import load_dotenv


class CLIManager:
    __CACHE_PATH = Path(Path.cwd() / ".barkoagent-cache.json")

    def __init__(self):
        load_dotenv('.env')
        self.requests_session = requests.Session()
        self.__token = os.getenv("TOKEN")
        self.__token_expiry = None
        endpoint_to_verify = os.getenv("URL")

        # Verify the URL is valid and correct
        self.__verify_correct_environment(endpoint_to_verify)
        self.__endpoint = endpoint_to_verify

        # Remove cache file if older than a day
        if os.path.isfile(self.__CACHE_PATH):
            current_modified_time = os.path.getmtime(self.__CACHE_PATH)
            modification_time = datetime.fromtimestamp(current_modified_time)
            now = datetime.now()
            time_delta = now - modification_time
            if time_delta.days > 0 and os.path.exists(self.__CACHE_PATH):
                os.remove(self.__CACHE_PATH)

        # Create new cache file then
        Path(self.__CACHE_PATH).touch()

    @classmethod
    def __verify_correct_environment(cls, url):
        reg_ex_result = re.search("https://[a-z]+\.barkoagent\.com",url)
        return reg_ex_result is not None

    def get_project_data(self, project_id):
        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.get(f'{self.__endpoint}/api/general/get-data/{project_id}', headers=headers, timeout=10)
        res.raise_for_status()
        raw_data = res.json()
        # Clean out the data for output
        project_info : dict = raw_data[1][0]
        project_info.pop('idx')

        chats_info = raw_data[2]
        chat_entries_info = raw_data[4]

        formatted_data = {
            'chats_size': len(chats_info),
            'chat_entries_size': len(chat_entries_info)
        }
        formatted_data = formatted_data | project_info
        return formatted_data

    def get_brain_status(self, project_id):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(f'{self.__endpoint}/api/chats/brain_status?project_id={project_id}', headers=headers, timeout=10)
        res.raise_for_status()
        brain_state = res.json()
        click.echo(f'Polling brain status: {brain_state['ready']}')
        return brain_state['ready']

    def run_single_script(self, project_id, chat_id):
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
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/run_script/{project_id}/{chat_id}', json=[], headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        existing_data = None
        with self.__CACHE_PATH.open("r", encoding="utf-8") as f:
            existing_data = json.load(f)
        with self.__CACHE_PATH.open("a", encoding="utf-8") as f:
            existing_data['tasks'] = data['submitted_tasks']
            json.dump(existing_data, f)
        return data

    def run_all_scripts(self, project_id):
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
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/run_script?project_id={project_id}', json=[], headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        existing_data = None
        with self.__CACHE_PATH.open("r", encoding="utf-8") as f:
            existing_data = json.load(f)

        with self.__CACHE_PATH.open("w", encoding="utf-8") as f:
            lst = []
            for chat_id, task_id in data['submitted_tasks'].items():
                lst.append({"chat_id": chat_id, "task_id": task_id})
            existing_data['tasks'] = lst
            json.dump(existing_data, f)
        return data

    def get_test_results(self, project_id):
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        existing_data = None
        with self.__CACHE_PATH.open("r", encoding="utf-8") as f:
            existing_data = json.load(f)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        chat_task_pairs = existing_data['tasks']
        res = self.requests_session.post(f'{self.__endpoint}/api/chats/script_results?project_id={project_id}', json=chat_task_pairs, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def get_batch_test_reports_list(self, project_id, limit=20, offset=0):

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(f'{self.__endpoint}/api/chats/project_reports/{project_id}?limit={limit}&offet={offset}',headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def get_batch_report_details(self, batch_report_id):

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

    def get_batch_executions(self, batch_report_id, limit=20, offset=0):
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

    def delete_batch_report(self, batch_report_id):
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

    def exit_client(self):
        if os.path.exists(self.__CACHE_PATH):
            os.remove(self.__CACHE_PATH)
        else:
            click.echo("Client encountered unexpected issue - MISSING CACHE FILE")




