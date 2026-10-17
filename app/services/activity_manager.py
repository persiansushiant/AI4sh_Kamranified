# Main-workspace navigation commands using numeric main-menu IDs. Commands are consumed by the shell.
from .workspace_context import services

class ActivityManager:
    @staticmethod
    # Resolve an enabled main-menu entry and queue its string activity ID for navigation.
    # A missing numeric menu ID raises during lookup.
    def open(id):
        s = services()
        with s.lock:
            item = s.registry[s.menu[id]]
            if not item.enabled:
                raise ValueError("Activity is disabled")
            s.command("activity.open", item.id)
