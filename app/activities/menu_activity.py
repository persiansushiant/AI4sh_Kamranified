# Demonstration of runtime menu and panel controls. Numeric IDs refer to existing
# menu registrations; they are not string activity IDs or filesystem paths.
from .activity_base import Activity
from .notes_activity import NotesActivity
from ..services.main_menu import MainMenu
from ..services.bottom_panel import BottomPanel
from ..services.activity_manager import ActivityManager
from ..services.activity_log import Log

class MenuActivity(Activity):
    # Register the menu-controls demonstration activity.
    def __init__(self): super().__init__("menu")

    # Dispatch a single named demo command. Missing or unknown commands raise an error.
    def run(self, payload):
        action = payload.get("action")
        # These commands use fixed demo menu IDs: ML=3, dynamic notes=5, open target=2.
        # Adding an already registered ID can fail; availability depends on current registrations.
        if action == "ml/enable": MainMenu.enable(3)
        elif action == "notes/add": MainMenu.add(5, "Dynamic activity", NotesActivity, "notebook-pen")
        elif action == "notes/remove": MainMenu.remove(5)
        elif action == "notes/enable": MainMenu.enable(5)
        elif action == "panel/open": BottomPanel.open()
        elif action == "panel/close": BottomPanel.close()
        elif action == "panel/height": BottomPanel.set_height(300)
        elif action == "activity/open": ActivityManager.open(2)
        else: raise ValueError("Unknown demo command")
        # Log only after the selected control call finishes successfully.
        Log.info(f"Executed {action}")
        return {"message": "Command executed."}
