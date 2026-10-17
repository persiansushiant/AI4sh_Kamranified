---
layout: default
title: "Validation and troubleshooting"
---

# Validation and troubleshooting


## Verify meaningful behavior

For feature changes, cover server-side input validation, allowed/locked actions, unchanged mode after failure, transaction rollback, persistence after restart, menu visibility and loading cleanup. Use temporary SQLite files and keys. Do not include test data in releases.

If an existing tests/ suite is present:

```powershell
.venv\Scripts\python -m pytest -q
```

This overlay does not add or claim an existing test count. Source inspection and documentation checks do not prove browser behavior.

## Manual check

1. Fresh private test configuration: workspace mode 0 shows only Configuration.
2. Invalid password: no configuration completion transition.
3. Valid save: settings survive restart and Import data opens.
4. Import mode 0: only Create Database is colored/clickable.
5. Placeholder click: pending implementation message; no stage transition.
6. Once real creation is implemented: mode 1 unlocks Setup Processes and Delete Database.
7. Once process setup succeeds: loaders unlock; deletion returns import stage to 0.
8. A direct POST for a locked action must still fail.
9. Error paths release loading and produce safe trace messages.
10. Keyboard focus and reduced-motion behavior remain usable.

## Troubleshooting

| Problem | Check |
|---|---|
| attempted relative import | Execute run.py from the root, not workspace_configuration.py |
| Duplicate activity ID | The same string ID cannot be in main and bottom registries |
| No traces visible | Register LogActivity in configure(); logging alone does not add the tab |
| Create Database gray | Inspect server import mode and aria-disabled before changing CSS |
| Changes not visible | Hard refresh after JS/CSS updates; inspect console and server errors |
| Stored values unreadable | Restore the matching database/key pair; do not replace the key |
| ML page never appears | Real import does not yet trigger the overall workspace transition |
| Pages styles or links fail | Set baseurl to the repository path, with leading slash and no trailing slash |

## Known integration constraints

The original SetupActivity still attempts to register ConfigurationSummaryActivity in BottomMenu ID 2. The newer main flow uses the same activity ID. Using both registrations causes a registry collision. Do not wire both flows simultaneously without an explicit rename or removal.

Menu demo numeric IDs 2/3/5 belong to the original demo. They are not the staged workspace IDs 20/21/22. Do not assume old demo navigation remains valid after changing startup registration.

The backbone has no authentication, durable background jobs, cancellation, schema migration framework, multi-worker coordination, or persistent trace audit store.
