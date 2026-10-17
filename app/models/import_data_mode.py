# Import-page stages and action permissions. These stages are separate from workspace.mode.
from enum import IntEnum


class ImportDataMode(IntEnum):
    # Only database creation is allowed in the initial stage.
    INITIAL = 0
    # Database creation unlocks process setup and deletion.
    DATABASE_READY = 1
    # Process setup unlocks data loaders; creation remains locked.
    PROCESSES_READY = 2
    DATA_READY = 3


# Import modes are independent of workspace.mode.
# Edit these immutable action-ID sets to change availability for each stage.
# Action IDs must match the controls definitions and activity handler mapping.
IMPORT_DATA_MODE_ACTIONS = {
    ImportDataMode.INITIAL: frozenset({"create_database"}),
    ImportDataMode.DATABASE_READY: frozenset({"setup_processes", "delete_database"}),
    ImportDataMode.PROCESSES_READY: frozenset({"setup_processes", "delete_database", "utility_data", "dataset_metadata", "sample_data", "wetlab_data", "spectral_data", "all_data"}),
    # Retained for compatibility with previously saved mode 3.
    ImportDataMode.DATA_READY: frozenset({"setup_processes", "delete_database", "utility_data", "dataset_metadata", "sample_data", "wetlab_data", "spectral_data", "all_data"}),
}
