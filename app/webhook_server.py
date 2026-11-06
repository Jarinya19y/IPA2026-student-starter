"""Part 4 student implementation."""

import json
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from app.integration import process_request
from app.webex_client import WEBEX_API_BASE, WebexClient

logger = logging.getLogger("webhook_server")
executor = ThreadPoolExecutor(max_workers=5)

class WebexEventHandler:
    def __init__(self, client, bot_person_id, processor=None):
        # TODO: implement according to Part 4 specification
        self.client = client
        self.bot_person_id = bot_person_id
        self.processor = processor or process_request

    def handle_event(self, event):
        # TODO: implement according to Part 4 specification
        if not isinstance(event, dict):
            return None

        resource = event.get("resource")
        event_type = event.get("event")
        data = event.get("data", {})

        if resource != "messages" or event_type != "created":
            return None

        message_id = data.get("id")
        if not message_id:
            return None

        person_id = data.get("personId")
        if person_id and person_id == self.bot_person_id:
            return None

        try:
            msg_data = self.client.get_message(message_id)
        except Exception as e:
            logger.error(f"Failed to fetch message {message_id}: {e}")
            return None

        author_id = msg_data.get("personId")
        if author_id and author_id == self.bot_person_id:
            return None

        room_id = msg_data.get("roomId")
        mentioned_people = msg_data.get("mentionedPeople", [])
        files = msg_data.get("files", [])

        # ไม่แนบไฟล์
        if not files:
            res = self.processor(mentioned_people, None, self.bot_person_id)
            self._reply(room_id, res)
            return res

        # แนบหลายไฟล์
        if len(files) > 1:
            res = {"status": "error", "result": "multiple_attachments"}
            self._reply(room_id, res)
            return res

        # แนบ 1 ไฟล์
        file_url = files[0]
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "request.yaml"
            try:
                content = self.client.download_file(file_url)
                with open(tmp_path, "wb") as f:
                    f.write(content)
                res = self.processor(
                    mentioned_people, str(tmp_path), self.bot_person_id
                )
            except Exception as e:
                logger.error(f"Error processing attachment: {e}")
                res = {"status": "error", "result": "invalid_yaml"}

            self._reply(room_id, res)
            return res

    def _reply(self, room_id, result):
        if room_id and result:
            try:
                self.client.send_message(
                    room_id, json.dumps(result, indent=2)
                )
            except Exception as e:
                logger.error(f"Failed to reply to room {room_id}: {e}")

def make_http_handler(submit_event):
    # TODO: implement according to Part 4 specification
    class WebhookHTTPHandler(BaseHTTPRequestHandler):

        def log_message(self, format, *args):
            pass

        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"status": "ok", "result": "healthy"}).encode(
                    "utf-8"
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/webhook":
                self.send_error(404)
                return

            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                content_length = 0

            if content_length < 1 or content_length > 1000000:
                self._send_400()
                return

            body = self.rfile.read(content_length)
            try:
                event_data = json.loads(body.decode("utf-8"))
            except Exception:
                self._send_400()
                return

            if not isinstance(event_data, dict):
                self._send_400()
                return

            submit_event(event_data)

            resp_body = json.dumps(
                {"status": "ok", "result": "accepted"}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)

        def _send_400(self):
            body = json.dumps(
                {"status": "error", "result": "invalid_event"}
            ).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return WebhookHTTPHandler

def main():
    # TODO: implement according to Part 4 specification
    token = os.getenv("WEBEX_BOT_TOKEN")
    client = WebexClient(token=token)

    # ดึง bot_person_id ผ่าน /v1/people/me
    import requests

    res = requests.get(
        f"{WEBEX_API_BASE}/people/me", headers=client.headers, timeout=10
    )
    res.raise_for_status()
    bot_person_id = res.json().get("id")

    event_handler = WebexEventHandler(client, bot_person_id)

    def submit_event(event):
        executor.submit(event_handler.handle_event, event)

    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", "8000"))

    handler_class = make_http_handler(submit_event)
    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"Starting server on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
