# Import action dispatcher. The controls service owns import-mode permissions
# and transitions; individual handlers below are extension points for real operations.
from .activity_base import Activity
from ..services.import_data_controls import get_import_data_state, require_import_data_action, complete_import_data_action
from ..services.execution_trace import Trace
import time
from ..services.progress_bar import ProgressBar

class ImportDataActivity(Activity):
    # Map stable payload action IDs to explicit Python methods.
    # Add new actions to both this mapping and the controls service definitions.
    ACTION_HANDLERS = {
        "create_database": "import_data_activity_create_database",
        "setup_processes": "import_data_activity_setup_processes",
        "delete_database": "import_data_activity_delete_database",
        "utility_data": "import_data_activity_utility_data",
        "dataset_metadata": "import_data_activity_dataset_metadata",
        "sample_data": "import_data_activity_sample_data",
        "wetlab_data": "import_data_activity_wetlab_data",
        "spectral_data": "import_data_activity_spectral_data",
        "all_data": "import_data_activity_all_data",
    }

    # Identify this activity independently of the numeric sidebar menu ID.
    def __init__(self):
        super().__init__("import_data")

    # Read current permissions for rendering enabled and locked controls; do not change the mode.
    def load(self):
        return get_import_data_state()

    # The browser sends an action ID. Validate its type and permissions before dispatch.
    def run(self, payload):
        action_id = payload.get("action")
        if not isinstance(action_id, str):
            raise ValueError("Action must be a string.")
        # Enforce mode permissions on the server even for direct POST requests.
        require_import_data_action(action_id)
        # Resolve the handler only after the server permission check succeeds.
        handler = getattr(self, self.ACTION_HANDLERS[action_id])
        return handler(payload)

    # A placeholder logs the request and returns the current state without advancing the mode.
    # implemented=False means the operation did not run; it is not a successful database action.
    def import_data_activity_placeholder(self, action_id):
        Trace.info("process", f"Import action requested: {action_id}; implementation pending.")
        return {"implemented": False, "message": "This action has not been implemented yet.",
                "state": get_import_data_state()}

    # Extension point: create the configured database. Do not advance on failure.
    def import_data_activity_create_database(self, payload):
        # Start progress and automatically reveal the Log activity.
        ProgressBar.start("Creating database...")

        try:
            # Simulate an operation so progress remains visible for three seconds.
            time.sleep(3)

            return self.import_data_activity_placeholder("create_database")
        finally:
            # Stop progress while keeping the Log panel open.
            ProgressBar.end()

    # Extension point: register process definitions after database creation succeeds.
    def import_data_activity_setup_processes(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("setup_processes")

    # Extension point: delete configured content; report completion only after actual deletion.
    def import_data_activity_delete_database(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("delete_database")

    # Extension point: load utility and lookup records.
    def import_data_activity_utility_data(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("utility_data")

    # Extension point: load dataset descriptions and identifiers.
    def import_data_activity_dataset_metadata(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("dataset_metadata")

    # Extension point: load sample records and related project data.
    def import_data_activity_sample_data(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("sample_data")

    # Extension point: load laboratory measurement records.
    def import_data_activity_wetlab_data(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("wetlab_data")

    # Extension point: load spectral observation records.
    def import_data_activity_spectral_data(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("spectral_data")

    # Extension point: orchestrate all data loaders in the required dependency order.
    def import_data_activity_all_data(self, payload):
        # Add this action's implementation here. Change mode only after success.
        return self.import_data_activity_placeholder("all_data")

    # Return a fresh permission state so the browser can update colors and click availability.
    # Call this helper only after real work succeeds; exceptions should leave the mode unchanged.
    def import_data_activity_success(self, action_id, message):
        # Each handler calls this after its real operation succeeds.
        state = complete_import_data_action(action_id)
        Trace.success("process", message)
        return {"implemented": True, "message": message, "state": state}
