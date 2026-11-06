"""Part 4 student implementation."""

from app.backends import ansible, netconf, netmiko_textfsm, restconf

def dispatch_request(data):
    # TODO: implement according to Part 4 specification
    router = str(data["router"])
    method = data["method"]
    action = data["action"]
    desired = data.get("desired", {})
    interface = desired.get("interface", {})
    interface_name = interface.get("name")

    # 1. RESTCONF
    if method == "restconf":
        if action == "status":
            return restconf.get_interface_state(router, interface_name)
        elif action == "plan":
            return restconf.plan_interface(router, interface)
        elif action == "apply":
            return restconf.apply_interface(router, interface)

    # 2. NETCONF
    elif method == "netconf":
        if action == "status":
            return netconf.get_interface_state(router, interface_name)
        elif action == "plan":
            return netconf.plan_interface(router, interface)
        elif action == "apply":
            return netconf.apply_interface(router, interface)

    # 3. Ansible
    elif method == "ansible":
        if action == "apply":
            return ansible.apply_interface(router, interface)

    # 4. Netmiko + TextFSM
    elif method == "netmiko-textfsm":
        if action == "status":
            return netmiko_textfsm.get_interface_state(router, interface_name)
        elif action == "delete":
            return netmiko_textfsm.delete_interface(router, interface_name)

    return {"status": "error", "result": "invalid_action"}
