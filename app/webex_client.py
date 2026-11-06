"""Part 4 student implementation."""

import os

import requests

WEBEX_API_BASE = 'https://webexapis.com/v1'

class WebexClient:
    def __init__(self, token=None, session=None):
        # TODO: implement according to Part 4 specification
        auth_token = token or os.getenv("WEBEX_BOT_TOKEN")
        if not auth_token:
            raise PermissionError("WEBEX_BOT_TOKEN is not provided.")
        self.token = auth_token
        self.session = session or requests.Session()

    @property
    def headers(self):
        # TODO: implement according to Part 4 specification
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_message(self, message_id):
        # TODO: implement according to Part 4 specification
        url = f"{WEBEX_API_BASE}/messages/{message_id}"
        res = self.session.get(url, headers=self.headers, timeout=10)
        res.raise_for_status()
        return res.json()

    def download_file(self, file_url):
        # TODO: implement according to Part 4 specification
        headers = {"Authorization": f"Bearer {self.token}"}
        res = self.session.get(file_url, headers=headers, timeout=10)
        res.raise_for_status()
        return res.content

    def send_message(self, room_id, text):
        # TODO: implement according to Part 4 specification
        url = f"{WEBEX_API_BASE}/messages"
        payload = {"roomId": room_id, "text": text}
        res = self.session.post(
            url, json=payload, headers=self.headers, timeout=10
        )
        res.raise_for_status()
        return res.json()
