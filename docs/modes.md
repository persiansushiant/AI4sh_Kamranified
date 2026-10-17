---
layout: default
title: "Modes and permissions"
---

# Modes and permissions


## Two independent state machines

| Key | Owner | Controls |
|---|---|---|
| `workspace.mode` | `services/workspace_mode.py` | Which main pages exist |
| `import_data.mode` | `models/import_data_mode.py`, `services/import_data_controls.py` | Which import operations are clickable |

A change to one key does not automatically change the other.

## Workspace modes

| Mode | Sidebar |
|---|---|
| 0 | 20 Configuration |
| 1 | 21 Import data |
| 2 | 21 Import data + 22 Machine learning |

`get_mode()` uses the legacy setup.completed flag when workspace.mode is absent or null. Valid stored values are integers 0, 1 or 2, not booleans.

`register_mode_activities()` removes IDs 20/21/22 and rebuilds the correct branch. Call it at startup or during an explicit transition; never from a read-only load request.

`complete_configuration()` saves credentials, setup.completed and at least workspace mode 1 atomically. It preserves a higher mode. On the initial transition it rebuilds and opens Import data.

`complete_import_demo()` advances workspace mode to 2 and records import.demo_completed. It is a demo helper, not proof that data exists. The current import handlers do not call it; there is no completed real-import-to-ML transition in this snapshot.

## Import modes

| Mode | Enabled actions |
|---|---|
| INITIAL / 0 | create_database |
| DATABASE_READY / 1 | setup_processes, delete_database |
| PROCESSES_READY / 2 | setup_processes, delete_database, all six loaders |
| DATA_READY / 3 | Same permissions as 2, retained for saved-state compatibility |

The six loaders are utility_data, dataset_metadata, sample_data, wetlab_data, spectral_data, and all_data. None currently implements its operation.

After actual creation succeeds, `complete_import_data_action("create_database")` sets mode 1. Actual process setup sets mode to at least 2. Actual deletion sets mode 0. Loading data does not itself change stage in this version.

## Extend an import action

1. Add its display definition to ACTION_DEFINITIONS.
2. Add its ID to the permitted modes in IMPORT_DATA_MODE_ACTIONS.
3. Add its mapping and method to ImportDataActivity.ACTION_HANDLERS.
4. Validate and perform real work in that handler.
5. Only after success call the activity success helper:

```python
return self.import_data_activity_success(
    "create_database",
    "Database created successfully.",
)
```

The helper returns fresh state to update button availability and colors. Exceptions must prevent success transitions. Placeholder handlers return implemented=False and leave the stage unchanged.

## Lock presentation

The server sends enabled and reason for each action. JS sets card data-locked and button aria-disabled. Locked controls keep hover/focus but reject clicks; require_import_data_action enforces the same permission on the server, including direct requests.
