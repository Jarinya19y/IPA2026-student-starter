import json
import os
import subprocess
import tempfile
from ipaddress import IPv4Interface
from pathlib import Path

ANSIBLE_DIR = Path(__file__).resolve().parents[2] / "ansible"


def error(code):
    return {"status": "error", "result": code}


def _real_run_playbook(variables):
    """รัน ansible-playbook จริงโดยแมปตัวแปรตรงกับ apply_interface.yml"""
    extra = dict(
        variables,
        ansible_host=variables["router"],
        target=variables["router"],
    )

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(extra, f)
        vars_file = f.name

    env = dict(
        os.environ,
        ANSIBLE_HOST_KEY_CHECKING="False",
        ANSIBLE_PERSISTENT_COMMAND_TIMEOUT="12",
        ANSIBLE_PERSISTENT_CONNECT_TIMEOUT="12",
    )
    try:
        proc = subprocess.run(
            [
                "ansible-playbook",
                "-i",
                str(ANSIBLE_DIR / "inventory.ini"),
                str(ANSIBLE_DIR / "apply_interface.yml"),
                "-e",
                f"@{vars_file}",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=18,
        )
    except subprocess.TimeoutExpired:
        raise ConnectionError("ansible-playbook timed out")
    finally:
        if os.path.exists(vars_file):
            os.unlink(vars_file)

    if proc.returncode == 0:
        return

    output = (proc.stdout + proc.stderr).lower()
    if "authentication" in output or "permission denied" in output:
        raise PermissionError("authentication failed")
    if "unreachable" in output or "timed out" in output or "timeout" in output:
        raise ConnectionError("router unreachable")
    raise RuntimeError("playbook failed")


def apply_interface(
    router,
    desired_interface,
    run_playbook=None,
):
    """Apply complete desired interface state using Ansible."""
    if run_playbook is None:
        run_playbook = _real_run_playbook

    admin_state = desired_interface.get("admin_state", "up")
    ipv4 = IPv4Interface(desired_interface["ipv4"])

    variables = {
        "router": router,
        "interface_name": desired_interface["name"],
        "description": desired_interface["description"],
        "ipv4_address": str(ipv4.ip),
        "netmask": str(ipv4.netmask),
        "shutdown": admin_state == "down",
    }

    try:
        run_playbook(variables)
    except PermissionError:
        return error("authentication_failed")
    except (ConnectionError, TimeoutError):
        return error("connection_failed")
    except Exception:
        return error("backend_failed")

    return {"status": "ok", "result": "applied"}
