import yaml

ALLOWED_ROUTERS = {
    "10.0.29.101",
    "10.0.29.102",
    "10.0.29.103",
    "10.0.29.104",
    "10.0.29.105",
}

METHODS_AND_ACTIONS = {
    "restconf": ["status", "plan", "apply"],
    "netconf": ["status", "plan", "apply"],
    "ansible": ["apply"],
    "netmiko-textfsm": ["status", "delete"],
}

def validate_request(data):
    """
    Validate one IPA2026 desired-state request.

    Return a response dictionary according to
    specs/response-spec-v1.md.
    """
    # TODO: implement
    # 1. version
    # A missing version or any other type/value returns invalid_version. 
    if "version" not in data or data["version"] is None:
        return {"status": "error", "result": "invalid_version"}
    
    # it must be the YAML integer 1.
    # In particular, "1" (string), 1.0 (float), and true (boolean) are invalid.
    version = data["version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        return {"status": "error", "result": "invalid_version"}

    # 2. router: 
    # missing_router
    if "router" not in data or data["router"] is None:
        return {"status": "error", "result": "missing_router"}
    # invalid_router if it is not one of the allowed router addresses.
    if str(data["router"]) not in ALLOWED_ROUTERS:
        return {"status": "error", "result": "invalid_router"}

    # 3. method:
    # missing_method 
    if "method" not in data or data["method"] is None:
            return {"status": "error", "result": "missing_method"}
    # , then invalid_method if unknown.
    method = data["method"]
    if method not in METHODS_AND_ACTIONS:
        return {"status": "error", "result": "invalid_method"}

    # 4. action: 
    # missing_action 
    if "action" not in data or data["action"] is None:
            return {"status": "error", "result": "missing_action"}
    # invalid_action if unsupported by the selected method.
    action = data["action"]
    if action not in METHODS_AND_ACTIONS[method]:
        return {"status": "error", "result": "invalid_action"}

    # 5. desired: 
    # desired:  missing_desired, 
    if "desired" not in data or data["desired"] is None:
        return {"status": "error", "result": "missing_desired"}
    # desired.interface:  missing_interface
    desired = data["desired"]
    if not isinstance(desired, dict) or "interface" not in desired or desired["interface"] is None:
        return {"status": "error", "result": "missing_interface"}
    # desired.interface.name:  missing_interface_name
    interface = desired["interface"]
    if not isinstance(interface, dict) or "name" not in interface or not interface["name"] or str(interface["name"]).strip() == "":
        return {"status": "error", "result": "missing_interface_name"}
    if "admin_state" in interface and interface["admin_state"] is not None:
        if interface["admin_state"] not in ("up", "down"):
            return {"status": "error", "result": "invalid_admin_state"}

    # 6. For plan and apply only: 
    if action in ("plan", "apply"):
        # missing_ipv4
        if "ipv4" not in interface or not interface["ipv4"] or str(interface["ipv4"]).strip() == "":
            return {"status": "error", "result": "missing_ipv4"}
        # missing_description
        if "description" not in interface or interface["description"] is None:
            return {"status": "error", "result": "missing_description"}
        # missing_admin_state
        if "admin_state" not in interface or interface["admin_state"] is None:
            return {"status": "error", "result": "missing_admin_state"}
        # invalid_admin_state
        if interface["admin_state"] not in ("up", "down"):
            return {"status": "error", "result": "invalid_admin_state"}

    # ผ่านการตรวจสอบ
    return {"status": "ok", "result": "accepted"}


def process_request_file(path):
    """
    Read a YAML request file, validate it,
    and return a response dictionary.
    """
    # TODO: implement
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        if not isinstance(data, dict):
            return {"status": "error", "result": "invalid_yaml"}
            
    except Exception:
        return {"status": "error", "result": "invalid_yaml"}

    return validate_request(data)
