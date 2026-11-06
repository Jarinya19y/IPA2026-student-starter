import os
import xml.etree.ElementTree as ET
import ipaddress
from .planning import plan_interface as generic_plan_interface
from ncclient import manager

def _convert_mask_to_cidr(netmask):
    return "/" + str(ipaddress.IPv4Network(f"0.0.0.0/{netmask}").prefixlen)

def _get_auth():
    username = os.getenv("ROUTER_USER")
    password = os.getenv("ROUTER_PASS")
    return (username, password)

def get_interface_state(
    router,
    interface_name,
    netconf_get_config=None,
):
    """Return normalized interface status using NETCONF."""
    filter_xml = f"""<interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
  <interface>
    <name>{interface_name}</name>
  </interface>
</interfaces>"""

    try:
        if netconf_get_config is not None:
            xml_text = netconf_get_config(router, filter_xml)
        else:
            username, password = _get_auth()
            with manager.connect(host=router, port=830, username=username, password=password, hostkey_verify=False) as m:
                res = m.get_config(source='running', filter=('subtree', filter_xml))
                xml_text = res.xml

        if not xml_text:
            return {"status": "ok", "result": "not_found", "interface": None}

        root = ET.fromstring(xml_text)
        interface_node = None
        for elem in root.iter():
            if elem.tag.endswith("interface"):
                name_elem = None
                for child in elem:
                    if child.tag.endswith("name"):
                        name_elem = child
                        break
                if name_elem is not None and name_elem.text == interface_name:
                    interface_node = elem
                    break

        if interface_node is None:
            return {"status": "ok", "result": "not_found", "interface": None}

        name = interface_name
        description = None
        enabled = True
        ip_addr = None
        netmask = None

        for child in interface_node:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "description":
                description = child.text
            elif tag == "enabled":
                enabled = child.text.lower() == "true"
            elif tag == "ipv4":
                for addr_node in child.iter():
                    sub_tag = addr_node.tag.split("}")[-1] if "}" in addr_node.tag else addr_node.tag
                    if sub_tag == "ip" and addr_node.text:
                        ip_addr = addr_node.text
                    elif sub_tag == "netmask" and addr_node.text:
                        netmask = addr_node.text

        ipv4_val = f"{ip_addr}{_convert_mask_to_cidr(netmask)}" if ip_addr and netmask else None
        admin_state = "up" if enabled else "down"

        return {
            "status": "ok",
            "result": "found",
            "interface": {
                "name": name,
                "ipv4": ipv4_val,
                "description": description,
                "admin_state": admin_state,
            },
        }

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}


def plan_interface(
    router,
    desired_interface,
    netconf_get_config=None,
):
    """Return create/update/no_change plan using NETCONF status."""
    return generic_plan_interface(
            router,
            desired_interface,
            lambda r, name: get_interface_state(r, name, netconf_get_config=netconf_get_config),
        )


def apply_interface(
    router,
    desired_interface,
    netconf_edit_config=None,
):
    """Apply complete desired interface state using NETCONF."""
    raw_name = desired_interface["name"]
    loopback_id = raw_name.replace("Loopback", "")

    ip_obj = ipaddress.IPv4Network(desired_interface["ipv4"], strict=False)
    ip_addr = str(ip_obj.network_address)
    netmask = str(ip_obj.netmask)

    shutdown_xml = "<shutdown/>" if desired_interface["admin_state"] == "down" else ""

    config_xml = f"""<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
  <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
    <interface>
      <Loopback nc:operation="replace">
        <name>{loopback_id}</name>
        <description>{desired_interface["description"]}</description>
        <ip>
          <address>
            <primary>
              <address>{ip_addr}</address>
              <mask>{netmask}</mask>
            </primary>
          </address>
        </ip>
        {shutdown_xml}
      </Loopback>
    </interface>
  </native>
</config>"""

    try:
        if netconf_edit_config is not None:
            netconf_edit_config(router, config_xml)
        else:
            username, password = _get_auth()
            from ncclient import manager
            with manager.connect(host=router, port=830, username=username, password=password, hostkey_verify=False) as m:
                m.edit_config(target='running', config=config_xml)

        return {"status": "ok", "result": "applied"}

    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}
