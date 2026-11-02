import os
from netmiko import ConnectHandler

def _get_auth():
    username = os.getenv("ROUTER_USER")
    password = os.getenv("ROUTER_PASS")
    return (username, password)

def get_interface_state(
    router,
    interface_name,
    netmiko_get=None,
):
    """Return normalized interface status using Netmiko + TextFSM."""
    try:
        if netmiko_get is not None:
            ip_info, descriptions = netmiko_get(router, interface_name)
        else:
            username, password = _get_auth()
            device = {
                "device_type": "cisco_ios",
                "host": router,
                "username": username,
                "password": password,
            }
            with ConnectHandler(**device) as net_connect:
                ip_info = net_connect.send_command(
                    f"show ip interface {interface_name}", use_textfsm=True
                )
                descriptions = net_connect.send_command(
                    "show interfaces description", use_textfsm=True
                )

        if not ip_info:
            return {"status": "ok", "result": "not_found", "interface": None}

        parsed_ip = ip_info[0] if isinstance(ip_info, list) and len(ip_info) > 0 else {}
        
        addr = parsed_ip.get("ip_address") or parsed_ip.get("ip")
        prefix = parsed_ip.get("prefix_length") or parsed_ip.get("prefix")
        link_state = parsed_ip.get("link_state") or parsed_ip.get("admin_state", "")

        if not addr or not prefix:
            return {"status": "ok", "result": "not_found", "interface": None}

        ipv4_val = f"{addr}/{prefix}"
        admin_state = "down" if "administratively down" in str(link_state).lower() else "up"

        desc_val = None
        short_name = interface_name.replace("Loopback", "Lo")
        for d in descriptions:
            if isinstance(d, dict):
                p_if = d.get("interface", "")
                if p_if in (interface_name, short_name):
                    desc_val = d.get("description")
                    break

        return {
            "status": "ok",
            "result": "found",
            "interface": {
                "name": interface_name,
                "ipv4": ipv4_val,
                "description": desc_val,
                "admin_state": admin_state,
            },
        }

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}


def delete_interface(
    router,
    interface_name,
    netmiko_delete=None,
):
    """Delete an interface using Netmiko."""
    try:
        if netmiko_delete is not None:
            res = netmiko_delete(router, interface_name)
            if res == "not_found":
                return {"status": "ok", "result": "not_found", "interface": None}
            elif res == "deleted":
                return {"status": "ok", "result": "deleted"}
            else:
                return {"status": "error", "result": "backend_failed"}
        else:
            username, password = _get_auth()
            device = {
                "device_type": "cisco_ios",
                "host": router,
                "username": username,
                "password": password,
            }
            with ConnectHandler(**device) as net_connect:
                # 1. เช็กสถานะก่อน
                status_res = get_interface_state(router, interface_name, netmiko_get=lambda r, n: (
                    net_connect.send_command(f"show ip interface {n}", use_textfsm=True),
                    net_connect.send_command("show interfaces description", use_textfsm=True)
                ))
                if status_res.get("result") == "not_found":
                    return {"status": "ok", "result": "not_found", "interface": None}

                # 2. ลบ interface
                net_connect.send_config_set([f"no interface {interface_name}"])

                # 3. ตรวจสอบอีกครั้ง
                status_check = get_interface_state(router, interface_name, netmiko_get=lambda r, n: (
                    net_connect.send_command(f"show ip interface {n}", use_textfsm=True),
                    net_connect.send_command("show interfaces description", use_textfsm=True)
                ))
                if status_check.get("result") == "not_found":
                    return {"status": "ok", "result": "deleted"}
                else:
                    return {"status": "error", "result": "backend_failed"}

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}
