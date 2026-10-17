# Bottom-panel activity registration and selection. Numeric IDs are local to this menu;
# string activity IDs are shared across the runtime registry and must be globally unique.
from .workspace_context import services
from ..activities.activity_base import Activity

class BottomMenu:
    @staticmethod
    # Accept an imported Activity subclass, instantiate it, and register its metadata.
    # Duplicate numeric menu IDs or globally registered activity IDs are rejected.
    def add(id, text, activity, icon, enabled=True):
        if not isinstance(id, int):
            raise ValueError("Menu ID must be an integer")
        if not isinstance(activity, type) or not issubclass(activity, Activity):
            raise ValueError("Pass an imported Activity class")
        s = services()
        with s.lock:
            if id in s.bottom_menu:
                raise ValueError(f"Menu ID {id} already exists")
            item = activity()
            if item.id in s.registry:
                raise ValueError(f"Activity {item.id} already exists")
            item.definition.title, item.definition.icon, item.definition.enabled = text, icon, enabled
            item.definition.placement = "bottom"
            s.registry[item.id] = item
            s.bottom_menu[id] = item.id

    @staticmethod
    # Remove both the menu mapping and activity registry entry; missing IDs are harmless.
    def remove(id):
        s = services()
        with s.lock:
            activity_id = s.bottom_menu.pop(id, None)
            if activity_id:
                s.registry.pop(activity_id, None)

    @staticmethod
    # Enable a registered entry and clear its previous disabled reason.
    def enable(id):
        s = services()
        with s.lock:
            item = s.registry[s.bottom_menu[id]]
            item.definition.enabled, item.definition.reason = True, ""

    @staticmethod
    # Keep the entry registered but prevent selection, with a reason for the UI.
    def disable(id, reason="Disabled"):
        s = services()
        with s.lock:
            item = s.registry[s.bottom_menu[id]]
            item.definition.enabled, item.definition.reason = False, reason

    @staticmethod
    # Check membership in the bottom-menu numeric ID namespace.
    def contains(id):
        s = services()
        with s.lock:
            return id in s.bottom_menu

    @staticmethod
    # Select and reload an enabled bottom activity. This does not reveal a closed panel;
    # call BottomPanel.open() separately when visibility should change.
    def open(id):
        s = services()
        with s.lock:
            item = s.registry[s.bottom_menu[id]]
            if not item.enabled:
                raise ValueError("Activity is disabled")
            s.command("bottom.open", item.id)
            s.command("bottom.reload", item.id)

    @staticmethod
    def ensure_log():
        """Create the built-in Log activity and its menu entry when missing."""
        # Import lazily to avoid an activity/service import cycle at startup.
        from ..activities.log_activity import LogActivity

        s = services()
        with s.lock:
            item = s.registry.get("log")
            if item is None:
                item = LogActivity()
                s.registry[item.id] = item
            if not isinstance(item, LogActivity):
                raise ValueError("Activity ID 'log' is reserved for LogActivity")
            item.definition.placement = "bottom"
            item.definition.enabled = True
            item.definition.reason = ""
            item.definition.icon = "scroll-text"
            if item.id not in s.bottom_menu.values():
                # Choose an unused internal ID without replacing existing entries.
                menu_id = -1
                while menu_id in s.bottom_menu:
                    menu_id -= 1
                s.bottom_menu[menu_id] = item.id
            return item.id

    @staticmethod
    def pop(id):
        """Reveal and select a bottom activity without removing or reloading it.

        Accept either a numeric menu ID or a registered bottom activity ID.
        Missing or disabled activities are rejected before a command is queued.
        """
        if id == "log":
            BottomMenu.ensure_log()
        s = services()
        with s.lock:
            activity_id = s.bottom_menu.get(id) if isinstance(id, int) else id
            if activity_id not in s.bottom_menu.values():
                raise ValueError(f"Bottom activity {id!r} is not registered")
            item = s.registry.get(activity_id)
            if item is None or not item.enabled:
                raise ValueError("Activity is disabled or unavailable")
            s.command("bottom.pop", activity_id)
