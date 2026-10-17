# Editable database configuration activity. Persistence and workspace-mode
# transitions are delegated to the workspace_mode service, not implemented here.
from .activity_base import Activity
from ..services.persistent_store import Store
from ..services.progress_bar import ProgressBar
from ..services.execution_trace import Trace
from ..services.workspace_mode import complete_configuration


class ConfigurationSummaryActivity(Activity):
    # Use the globally unique activity ID to select the matching HTML and JS files.
    def __init__(self):
        super().__init__("configuration_summary")

    # Return saved form values without modifying persistence or menus.
    # The password is intended only for this local masked input; do not trace these values.
    def load(self):
        data = Store.get("database.configuration", {})
        # Treat an unexpected stored value as an empty configuration.
        if not isinstance(data, dict):
            data = {}
        return {key: data.get(key, "") for key in ("database_name", "username", "password")}

    # Validate on the server as well as in the browser, before saving any values.
    def run(self, payload):
        name = payload.get("database_name")
        username = payload.get("username")
        password = payload.get("password")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Database name is required.")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Database username is required.")
        # The minimum is six characters, not six numeric digits; preserve password whitespace.
        if not isinstance(password, str) or len(password) < 6:
            raise ValueError("Password must contain at least 6 characters.")
        # Acquire the shared loading overlay only after validation succeeds.
        ProgressBar.start("Saving configuration…")
        try:
            # Save through the service, which also manages the configuration completion transition.
            complete_configuration({"database_name": name.strip(), "username": username.strip(), "password": password})
            # Record only the outcome, never the credential payload.
            Trace.success("sql", "Database configuration saved.")
            return {"message": "Configuration saved successfully."}
        # Always release the overlay, including persistence or menu-update failures.
        finally:
            ProgressBar.end()
