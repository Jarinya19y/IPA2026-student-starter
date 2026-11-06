import os
import ipaddress


def apply_interface(
    router,
    desired_interface,
    run_playbook=None,
):
    """Apply complete desired interface state using Ansible."""
    username = os.getenv("ROUTER_USER", "admin")
    password = os.getenv("ROUTER_PASS", "cisco")

    desired_ipv4 = desired_interface.get("ipv4", "")
    if "/" in desired_ipv4:
        ipv4_addr, prefix_len = desired_ipv4.split("/", 1)
        netmask = str(ipaddress.IPv4Network(f"0.0.0.0/{prefix_len}").netmask)
    else:
        ipv4_addr, prefix_len, netmask = desired_ipv4, "", ""

    admin_state = desired_interface.get("admin_state", "up")
    shutdown_flag = admin_state == "down"

    variables = {
        "router": router,
        "interface_name": desired_interface["name"],
        "ipv4": desired_ipv4,
        "ipv4_address": ipv4_addr,
        "ipv4_prefix_len": prefix_len,
        "netmask": netmask,
        "description": desired_interface["description"],
        "admin_state": admin_state,
        "shutdown": shutdown_flag,
        "ansible_user": username,
        "ansible_password": password,
    }

    try:
        if run_playbook is not None:
            run_playbook(variables)
        else:
            import ansible_runner

            res = ansible_runner.run(
                playbook="ansible/playbook.yaml", extravars=variables
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
