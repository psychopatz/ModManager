import re

def sanitize_path(name):
    """Sanitize and truncate names for folder safety."""
    if not name: return "General"
    clean = re.sub(r'[<>:"/\\|?*;]', '_', name)
    return clean[:50].strip()
