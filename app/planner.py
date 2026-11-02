def build_plan(desired_interface, current_interface):
    """
    Compare desired interface state with normalized current state
    and return a plan according to specs/plan-spec-v1.md.
    """
    # TODO: implement
    managed_fields = ["ipv4", "description", "admin_state"]

    changes = {}
    # None if the interface does not currently exist.
    if current_interface is None:
        for field in managed_fields:
            changes[field] = {"to": desired_interface[field]}

        return {
            "status": "ok",
            "result": "planned",
            "operation": "create",
            "changes": changes,
        }

    # กรณี 2 และ 3: update หรือ no_change - เมื่อมี interface อยู่แล้ว
    for field in managed_fields:
        desired_val = desired_interface.get(field)
        current_val = current_interface.get(field)
        
        # บันทึกความเปลี่ยนแปลงหากค่าในฟิลด์ไม่ตรงกัน
        if desired_val != current_val:
            changes[field] = {
                "from": current_val,
                "to": desired_val,
            }

    # Use update when the interface exists and 
    # at least one managed field differs from the desired state.
    if changes:
        operation = "update"
    # Use no_change when all managed fields already match the desired state.
    else: 
        operation = "no_change"

    return {
        "status": "ok",
        "result": "planned",
        "operation": operation,
        "changes": changes,
    }
