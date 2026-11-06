import ipaddress
import requests
import os
from .planning import plan_interface as generic_plan_interface


def _convert_mask_to_cidr(netmask):
    return "/" + str(ipaddress.IPv4Network(f"0.0.0.0/{netmask}").prefixlen)


def _get_auth():
    username = os.getenv("ROUTER_USER")
    password = os.getenv("ROUTER_PASS")
    return (username, password)


def get_interface_state(
    router,
    interface_name,
    http_get=None,
):
    """Return normalized interface status using RESTCONF."""

    url = (
        f"https://{router}/restconf/data/"
        f"ietf-interfaces:interfaces/interface={interface_name}"
    )

    try:
        if http_get is not None:
            res = http_get(url)
        else:
            res = requests.get(
                url,
                headers={"Accept": "application/yang-data+json"},
                auth=_get_auth(),
                verify=False,
                timeout=10,
            )

        status_code = getattr(res, "status_code", None)
        if status_code == 404:
            return {"status": "ok", "result": "not_found", "interface": None}
        elif status_code in (401, 403):
            return {"status": "error", "result": "authentication_failed"}
        elif status_code != 200:
            return {"status": "error", "result": "backend_failed"}

        data = res.json()
        if "ietf-interfaces:interface" in data:
            if_data = data["ietf-interfaces:interface"]
        elif "interface" in data:
            if_data = data["interface"]
        else:
            return {"status": "error", "result": "backend_failed"}

        name = if_data.get("name", interface_name)
        desc = if_data.get("description", None)
        enabled = if_data.get("enabled", True)
        admin_state = "up" if enabled else "down"

        ipv4_info = if_data.get("ietf-ip:ipv4", {}).get("address", [])
        if not ipv4_info:
            ipv4_info = if_data.get("ipv4", {}).get("address", [])

        ipv4_val = None
        if ipv4_info and isinstance(ipv4_info, list) and len(ipv4_info) > 0:
            addr = ipv4_info[0].get("ip")
            netmask = ipv4_info[0].get("netmask")
            if addr and netmask:
                ipv4_val = f"{addr}{_convert_mask_to_cidr(netmask)}"

        return {
            "status": "ok",
            "result": "found",
            "interface": {
                "name": name,
                "ipv4": ipv4_val,
                "description": desc,
                "admin_state": admin_state,
            },
        }

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except requests.exceptions.Timeout:
        return {"status": "error", "result": "connection_failed"}
    except requests.exceptions.RequestException:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}


def plan_interface(
    router,
    desired_interface,
    http_get=None,
):
    """Return create/update/no_change plan using RESTCONF status."""
    return generic_plan_interface(
        router,
        desired_interface,
        lambda r, name: get_interface_state(r, name, http_get=http_get),
    )


def apply_interface(
    router,
    desired_interface,
    http_put=None,
):
    """Apply complete desired interface state using RESTCONF."""
    raw_name = desired_interface["name"]
    loopback_id = raw_name.replace("Loopback", "")
    url = (
        f"https://{router}/restconf/data/"
        f"Cisco-IOS-XE-native:native/interface/Loopback={loopback_id}"
    )

    ip_obj = ipaddress.IPv4Network(desired_interface["ipv4"], strict=False)
    ip_addr = str(ip_obj.network_address)
    netmask = str(ip_obj.netmask)

    payload = {
        "Cisco-IOS-XE-native:Loopback": {
            "name": int(loopback_id) if loopback_id.isdigit() else loopback_id,
            "description": desired_interface["description"],
            "ip": {
                "address": {
                    "primary": {
                        "address": ip_addr,
                        "mask": netmask,
                    }
                }
            },
        }
    }

    if desired_interface["admin_state"] == "down":
        payload["Cisco-IOS-XE-native:Loopback"]["shutdown"] = [None]

    try:
        if http_put is not None:
            res = http_put(url, json=payload)
        else:
            res = requests.put(
                url,
                headers={"Content-Type": "application/yang-data+json"},
                json=payload,
                auth=_get_auth(),
                verify=False,
                timeout=10,
            )

        status_code = getattr(res, "status_code", None)
        if status_code in (200, 201, 204):
            return {"status": "ok", "result": "applied"}
        elif status_code in (401, 403):
            return {"status": "error", "result": "authentication_failed"}
        else:
            return {"status": "error", "result": "backend_failed"}

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except requests.exceptions.Timeout:
        return {"status": "error", "result": "connection_failed"}
    except requests.exceptions.RequestException:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}
