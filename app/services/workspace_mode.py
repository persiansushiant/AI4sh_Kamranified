# Persisted overall workspace stage and sidebar registration. This mode is independent
# of the import-page stage that controls individual action buttons.
from .persistent_store import Store
from .main_menu import MainMenu
from .activity_manager import ActivityManager

# Reserve these numeric IDs exclusively for the staged sidebar pages.
CONFIGURATION_MENU_ID = 20
IMPORT_DATA_MENU_ID = 21
MACHINE_LEARNING_MENU_ID = 22
MODE_KEY = "workspace.mode"


# Read workspace mode 0, 1, or 2. If absent or null, interpret the older setup.completed flag
# without writing a migration record during this read.
def get_mode():
    mode = Store.get(MODE_KEY, None)
    if mode is None:
        # Migrate the completion flag used before modes were introduced.
        return 1 if Store.get("setup.completed", False) else 0
    if type(mode) is not int or mode not in (0, 1, 2):
        raise ValueError("Workspace mode must be 0, 1 or 2.")
    return mode


# Rebuild only reserved main-menu IDs 20, 21, and 22 for the current stage.
# Mode 0 shows Configuration; mode 1 shows Import data; mode 2 shows Import data and ML.
def register_mode_activities():
    # Call only at startup or after a successful transition, never from load().
    # Local imports defer activity loading until registration and avoid top-level import cycles.
    from ..activities.configuration_summary_activity import ConfigurationSummaryActivity
    from ..activities.import_data_activity import ImportDataActivity
    from ..activities.machine_learning_activity import MachineLearningActivity

    mode = get_mode()

    # Clear previous staged registrations before rebuilding, without touching other menu IDs.
    for menu_id in (20, 21, 22):
        MainMenu.remove(menu_id)

    if mode == 0:
        MainMenu.add(
            20, "Configuration",
            ConfigurationSummaryActivity, "settings",
        )

    elif mode == 1:
        MainMenu.add(
            21, "Import data",
            ImportDataActivity, "database",
        )

    elif mode == 2:
        MainMenu.add(
            21, "Import data",
            ImportDataActivity, "database",
        )
        MainMenu.add(
            22, "Machine learning",
            MachineLearningActivity, "brain",
        )

# Save credentials, completion flag, and workspace mode in one transaction.
# Preserve an advanced mode; only the first completion rebuilds navigation and opens Import data.
def complete_configuration(configuration):
    previous = get_mode()
    # Persistence completes before runtime menu changes; registry updates are not part of this transaction.
    Store.set_many({
        "database.configuration": configuration,
        "setup.completed": True,
        MODE_KEY: max(previous, 1),
    })
    if previous == 0:
        register_mode_activities()
        ActivityManager.open(IMPORT_DATA_MENU_ID)


# Advance overall workspace mode for demonstration purposes only.
# This does not copy a database or advance import_data.mode.
def complete_import_demo():
    previous = get_mode()
    if previous < 1:
        raise ValueError("Save the database configuration first.")
    # This records a demo transition, not a successful database import.
    # Persistence completes before runtime menu changes; registry updates are not part of this transaction.
    Store.set_many({MODE_KEY: 2, "import.demo_completed": True})
    if previous < 2:
        register_mode_activities()
        ActivityManager.open(MACHINE_LEARNING_MENU_ID)
