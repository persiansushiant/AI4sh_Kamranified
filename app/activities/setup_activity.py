# Original setup flow: save configuration, then open a bottom-panel configuration view.
# This flow uses setup.completed and does not call the newer workspace-mode transition service.
from .activity_base import Activity
from .configuration_summary_activity import ConfigurationSummaryActivity
from ..services.bottom_menu import BottomMenu
from ..services.bottom_panel import BottomPanel
from ..services.progress_bar import ProgressBar
from ..services.execution_trace import Trace
from ..services.persistent_store import Store

class SetupActivity(Activity):
    # Use the original setup activity ID, separate from configuration_summary.
    def __init__(self): super().__init__("setup")

    # Return the saved configuration directly for the setup form. This is a read-only request.
    def load(self):
        return Store.get("database.configuration", {})

    # Validate all three fields before persistence. This original flow requires nonblank strings
    # and a maximum length of 500; it does not enforce the newer six-character password minimum.
    def run(self, payload):
        values = {}
        for field in ("database_name", "username", "password"):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} is required")
            if len(value) > 500:
                raise ValueError(f"{field} is too long")
            # Trim names, but preserve the password exactly as entered.
            values[field] = value if field == "password" else value.strip()
        # Show shared loading during save and panel registration.
        ProgressBar.start("Saving configuration…")
        try:
            Trace.info("scheme", "Saving database configuration")
            # Persist credentials and the completion flag in one transaction.
            Store.set_many({
                "database.configuration": values,
                "setup.completed": True,
            })
            # Avoid duplicate bottom-menu registration. The numeric ID 2 belongs to BottomMenu.
            # This registration must remain compatible with any main-menu registration of the same activity.
            if not BottomMenu.contains(2):
                BottomMenu.add(2, "Configuration summary", ConfigurationSummaryActivity, "database")
            # Select the bottom activity, then reveal its panel with a separate call.
            BottomMenu.open(2)
            BottomPanel.open()
            Trace.success("sql", "Configuration stored through ORM")
            return {"message": "Configuration saved.", "completed": True}
        # Release the loading overlay even if saving or bottom-panel setup fails.
        finally:
            ProgressBar.end()
