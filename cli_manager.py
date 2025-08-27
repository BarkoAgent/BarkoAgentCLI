import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import polling2
import click
from dotenv import load_dotenv


class CLIManager:
    __CACHE_PATH = Path(Path.cwd() / ".barkoagent-cache.json")

    def __init__(self):
        load_dotenv('.env')
        self.requests_session = requests.Session()
        self.__token = None
        self.__token_expiry = None

        # Remove cache file if older than a day
        if os.path.isfile(self.__CACHE_PATH):
            current_modified_time = os.path.getmtime(self.__CACHE_PATH)
            modification_time = datetime.fromtimestamp(current_modified_time)
            now = datetime.now()
            time_delta = now - modification_time
            if time_delta.days > 0 and os.path.exists(self.__CACHE_PATH):
                os.remove(self.__CACHE_PATH)

    def _read_token(self):
        with open(self.__CACHE_PATH) as f:
            config_file = json.load(f)
            self.__token = config_file['token']


    def get_local_user_token(self):
        user_email = os.getenv("USER_EMAIL")
        user_password = os.getenv("USER_PASSWORD")

        url = "http://localhost:8345/api/users/login"

        payload = {
            "username": user_email, "password": user_password
        }
        headers = {
            'Content-Type': 'application/json',
            'Allow': 'application/json',
        }
        response = self.requests_session.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        self.__token = data['accessToken']
        self.__token_expiry = datetime.now(timezone.utc) + (timedelta(hours=24))
        with self.__CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump({"token": self.__token}, f)
        return data

    def get_project_data(self, project_id):
        self._read_token()
        url = f'http://localhost:8345/api/general/get-data/{project_id}'
        headers = {
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.get(url, headers=headers, timeout=10)
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
        if not self.__token:
            self._read_token()
        url = f'http://localhost:8345/api/chats/brain_status?project_id={project_id}'
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        res = self.requests_session.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        brain_state = res.json()
        click.echo(f'Polling brain status: {brain_state['ready']}')
        return brain_state['ready']

    def run_single_script(self, project_id, chat_id):
        self._read_token()
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        url = f'http://localhost:8345/api/chats/run_script/{project_id}/{chat_id}'
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.post(url, json=[], headers=headers, timeout=10)
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
        self._read_token()
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        url = f'http://localhost:8345/api/chats/run_script?project_id={project_id}'
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }
        res = self.requests_session.post(url, json=[], headers=headers, timeout=10)
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
        self._read_token()
        # Poll brain_status until ready
        polling2.poll(
            lambda: self.get_brain_status(project_id) == True,
            step=2,
            poll_forever=True
        )
        existing_data = None
        with self.__CACHE_PATH.open("r", encoding="utf-8") as f:
            existing_data = json.load(f)

        url = f"http://localhost:8345/api/chats/script_results?project_id={project_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.__token}",
            "Accept": "application/json",
        }

        chat_task_pairs = existing_data['tasks']
        res = self.requests_session.post(url, json=chat_task_pairs, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data

    def exit_client(self):
        if os.path.exists(self.__CACHE_PATH):
            os.remove(self.__CACHE_PATH)
        else:
            click.echo("Client encountered unexpected issue - MISSING CACHE FILE")




