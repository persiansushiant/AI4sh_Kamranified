# Import action dispatcher. The controls service owns import-mode permissions
# and transitions; individual handlers below are extension points for real operations.
from .activity_base import Activity
from ..services.import_data_controls import get_import_data_state, require_import_data_action
from ..services.execution_trace import Trace
from ..services.notebook_runner import run_notebook
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

    def _run_notebook_action(self, action_id, text):
        ProgressBar.start(text)
        try:
            run_notebook(action_id, interactive=True)
            return self.import_data_activity_success(action_id, "Notebook completed successfully.")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            # Runtime marks the job failed; return current card state in its result.
            error = RuntimeError("Execution failed. Please check the log.")
            error.result = {"message": str(error), "state": get_import_data_state()}
            raise error from None
        finally:
            ProgressBar.end()

    def import_data_activity_create_database(self, payload):
        return self._run_notebook_action("create_database", "Creating database…")

    def import_data_activity_setup_processes(self, payload):
        return self._run_notebook_action("setup_processes", "Setting up processes…")

    def import_data_activity_delete_database(self, payload):
        return self._run_notebook_action("delete_database", "Deleting database…")

    # Extension point: load utility and lookup records.
    def import_data_activity_utility_data(self, payload):
        return self._run_notebook_action("utility_data", "Loading utility data…")

    # Extension point: load dataset descriptions and identifiers.
    def import_data_activity_dataset_metadata(self, payload):
        return self._run_notebook_action("dataset_metadata", "Loading dataset metadata…")

    # Extension point: load sample records and related project data.
    def import_data_activity_sample_data(self, payload):
        return self._run_notebook_action("sample_data", "Loading sample data…")

    # Extension point: load laboratory measurement records.
    def import_data_activity_wetlab_data(self, payload):
        return self._run_notebook_action("wetlab_data", "Loading wetlab data…")

    # Extension point: load spectral observation records.
    def import_data_activity_spectral_data(self, payload):
        return self._run_notebook_action("spectral_data", "Loading spectral data…")

    # Extension point: orchestrate all data loaders in the required dependency order.
    def import_data_activity_all_data(self, payload):
        return self._run_notebook_action("all_data", "Loading all data…")

    # Return a fresh permission state so the browser can update colors and click availability.
    # Call this helper only after real work succeeds; exceptions should leave the mode unchanged.
    def import_data_activity_success(self, action_id, message):
        # Each handler calls this after its real operation succeeds.
        state = get_import_data_state()
        Trace.success("process", message)
        return {"implemented": True, "message": message, "state": state}
