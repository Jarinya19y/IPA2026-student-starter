"""Part 4 student implementation."""

from app.core import process_request_file
from app.dispatcher import dispatch_request
from app.request_handler import validate_webex_envelope


def process_request(mentioned_people, attachment_path, bot_person_id):
    # TODO: implement according to Part 4 specification
    envelope_error = validate_webex_envelope(
        mentioned_people, attachment_path, bot_person_id
    )
    if envelope_error is not None:
        return envelope_error

    validation_res = process_request_file(attachment_path)
    if validation_res.get("status") != "ok":
        return validation_res

    # อ่านไฟล์ YAML เพื่อนำ data มา dispatch
    import yaml

    try:
        with open(attachment_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return {"status": "error", "result": "invalid_yaml"}

    return dispatch_request(data)
