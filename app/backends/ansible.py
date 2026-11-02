import os

def apply_interface(
    router,
    desired_interface,
    run_playbook=None,
):
    """Apply complete desired interface state using Ansible."""
    username = os.getenv("ROUTER_USER", "admin")
    password = os.getenv("ROUTER_PASS", "cisco")

    variables = {
        "router": router,
        "interface_name": desired_interface["name"],
        "ipv4": desired_interface["ipv4"],
        "description": desired_interface["description"],
        "admin_state": desired_interface["admin_state"],
        "ansible_user": username,
        "ansible_password": password,
    }

    try:
        if run_playbook is not None:
            run_playbook(variables)
        else:
            import ansible_runner
            res = ansible_runner.run(
                playbook='ansible/playbook.yaml',
                extravars=variables
            )
            if res.rc != 0:
                return {"status": "error", "result": "backend_failed"}

        return {"status": "ok", "result": "applied"}

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}
