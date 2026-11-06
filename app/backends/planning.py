from app.planner import build_plan


def plan_interface(
    router,
    desired_interface,
    get_interface_state,
):
    """Build a Part 2 plan from backend status."""
    resp = get_interface_state(router, desired_interface["name"])

    # backend error
    if resp.get("status") == "error":
        return resp

    # Part 2 receive normalized interface dictionary or None.
    if resp.get("result") == "found":
        current_interface = resp.get("interface")
    else:  # not_found
        current_interface = None

    return build_plan(desired_interface, current_interface)
