# Import-page action definitions, persisted stage, permission checks, and success transitions.
# These functions use import_data.mode; overall sidebar visibility uses workspace.mode.
from ..models.import_data_mode import ImportDataMode, IMPORT_DATA_MODE_ACTIONS
from .persistent_store import Store

# Stable persistence key for this page, separate from workspace.mode.
MODE_KEY = "import_data.mode"

# Canonical display definitions. The browser uses section to group cards and icon to select artwork.
# These definitions describe actions; they do not implement them.
ACTION_DEFINITIONS = (
    {"id": 'create_database', "title": 'Create Database', "description": 'Create the PostgreSQL database and its structures.', "icon": 'database', "section": 'setup'},
    {"id": 'setup_processes', "title": 'Setup Processes', "description": 'Register process definitions and dependencies.', "icon": 'workflow', "section": 'setup'},
    {"id": 'delete_database', "title": 'Delete Database', "description": 'Delete the configured database content.', "icon": 'trash', "section": 'setup'},
    {"id": 'utility_data', "title": 'Utility Data', "description": 'Load shared utility and lookup records.', "icon": 'wrench', "section": 'data'},
    {"id": 'dataset_metadata', "title": 'Dataset Metadata', "description": 'Load dataset descriptions and identifiers.', "icon": 'list', "section": 'data'},
    {"id": 'sample_data', "title": 'Sample Data', "description": 'Load sample records and project information.', "icon": 'box', "section": 'data'},
    {"id": 'wetlab_data', "title": 'Wetlab Data', "description": 'Load laboratory measurements.', "icon": 'droplet', "section": 'data'},
    {"id": 'spectral_data', "title": 'Spectral Data', "description": 'Load spectral observations.', "icon": 'activity', "section": 'data'},
    {"id": 'all_data', "title": 'All Data in One Go', "description": 'Run the data-loading workflows in order.', "icon": 'layers', "section": 'data'},
 )


# Restore the persisted import stage, defaulting to INITIAL for an absent key.
# Strict type checking rejects booleans; enum conversion rejects unknown integers.
def get_import_data_mode():
    value = Store.get(MODE_KEY, 0)
    if type(value) is not int:
        raise ValueError("Import data mode must be an integer.")
    return ImportDataMode(value)


# Validate the stage and persist its integer value. This alone does not refresh the UI.
def set_import_data_mode(mode):
    if isinstance(mode, bool) or not isinstance(mode, (int, ImportDataMode)):
        raise ValueError("Invalid import data mode.")
    Store.set(MODE_KEY, int(ImportDataMode(mode)))


# Build serializable action metadata with enabled flags and lock explanations.
# This read-only function neither changes the stage nor performs database operations.
def get_import_data_state():
    mode = get_import_data_mode()
    allowed = IMPORT_DATA_MODE_ACTIONS[mode]
    statuses = Store.get("import_data.actions", {})
    return {
        "mode": int(mode),
        "mode_name": mode.name.replace("_", " ").title(),
        "actions": [dict(action, status=Store.get(
                         "import_data." + action["id"] + ".status",
                         statuses.get(action["id"], {}).get("status", "not_started")),
                         enabled=action["id"] in allowed,
                         reason="" if action["id"] in allowed else "Unavailable in the current import mode.")
                    for action in ACTION_DEFINITIONS],
    }


# Reject unknown or currently locked actions before invoking a handler.
# Server validation remains necessary even when browser buttons appear locked.
def require_import_data_action(action_id):
    if action_id not in {action["id"] for action in ACTION_DEFINITIONS}:
        raise ValueError("Unknown import action.")
    if action_id not in IMPORT_DATA_MODE_ACTIONS[get_import_data_mode()]:
        raise ValueError("This action is unavailable in the current import mode.")


# Apply stage transitions only after real work succeeds, then return fresh UI state.
# This function does not execute the database or data-loading operation itself.
def complete_import_data_action(action_id):
    """Call only after the real action finishes successfully."""
    require_import_data_action(action_id)
    mode = get_import_data_mode()
    statuses = Store.get("import_data.actions", {})
    if action_id == "create_database":
        mode = ImportDataMode.DATABASE_READY
        statuses = {}
    elif action_id == "setup_processes":
        mode = max(mode, ImportDataMode.PROCESSES_READY)
    elif action_id == "delete_database":
        mode = ImportDataMode.INITIAL
        statuses = {}
    from datetime import datetime, timezone
    statuses[action_id] = {"status": "succeeded", "updated_at": datetime.now(timezone.utc).isoformat()}
    Store.set_many({MODE_KEY: int(mode), "import_data.actions": statuses})
    return get_import_data_state()


def record_action_status(action_id, status):
    from datetime import datetime, timezone
    statuses = Store.get("import_data.actions", {})
    statuses[action_id] = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    Store.set("import_data.actions", statuses)


def recover_interrupted_actions():
    # An independently running notebook may still be active when the UI opens.
    # Status values belong to notebook code; startup must not rewrite them.
    return None
