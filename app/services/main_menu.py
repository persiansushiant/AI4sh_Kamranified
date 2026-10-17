# Main sidebar registration and availability controls. Entries exist in runtime memory;
# startup configuration must rebuild entries from persisted completion state.
from .workspace_context import services
from ..activities.activity_base import Activity

class MainMenu:
    @staticmethod
    # Register an imported Activity subclass using a numeric sidebar ID.
    # The activity string ID must also be absent from the shared registry.
    def add(id, text, activity, icon, enabled=True):
        if not isinstance(id, int):
            raise ValueError("Menu ID must be an integer")
        if not isinstance(activity, type) or not issubclass(activity, Activity):
            raise ValueError("Pass an imported Activity class")
        s = services()
        with s.lock:
            if id in s.menu:
                raise ValueError(f"Menu ID {id} already exists")
            item = activity()
            if item.id in s.registry:
                raise ValueError(f"Activity {item.id} already exists")
            item.definition.title, item.definition.icon, item.definition.enabled = text, icon, enabled
            s.registry[item.id] = item
            s.menu[id] = item.id

    @staticmethod
    # Remove the mapping and registry item; removing a missing menu ID is harmless.
    def remove(id):
        s = services()
        with s.lock:
            activity_id = s.menu.pop(id, None)
            if activity_id:
                s.registry.pop(activity_id, None)

    @staticmethod
    # Allow selection again and clear the displayed disabled reason.
    def enable(id):
        s = services()
        with s.lock:
            item = s.registry[s.menu[id]]
            item.definition.enabled, item.definition.reason = True, ""

    @staticmethod
    # Prevent selection while preserving the menu item and explaining why it is locked.
    def disable(id, reason="Disabled"):
        s = services()
        with s.lock:
            item = s.registry[s.menu[id]]
            item.definition.enabled, item.definition.reason = False, reason
