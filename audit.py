from datetime import datetime
from typing import List, Dict, Any, Optional

# In-memory storage for our audit logs (since we don't need a DB)
_audit_trail: List[Dict[str, Any]] = []

def log_action(action: str, detail: str, result: str, order_id: Optional[str] = None) -> None:
    """
    Logs an action to the in-memory audit trail.
    
    Args:
        action (str): The high-level action being performed (e.g., "AI selected product").
        detail (str): Detailed explanation or reasoning (e.g., "Chose X because Y").
        result (str): The outcome of the action (e.g., "success", "failed", "declined").
        order_id (Optional[str]): Generated order reference for checkout-related actions.
    """
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "detail": detail,
        "result": result
    }
    if order_id:
        entry["order_id"] = order_id

    _audit_trail.append(entry)
    # Also print to terminal for debugging (safely handle Windows console encoding for ₹)
    try:
        print(f"[AUDIT] {entry['timestamp']} | {action} | {result} | {detail.replace('₹', 'Rs.')}")
        if order_id:
            print(f"[AUDIT] Order ID: {order_id}")
    except Exception:
        pass

def get_audit_trail() -> List[Dict[str, Any]]:
    """
    Returns the entire audit trail in reverse chronological order (newest first).
    """
    return _audit_trail[::-1]
