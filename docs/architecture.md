---
layout: default
title: "Architecture and ownership"
---

# Architecture and ownership


## Workspace regions

| Region | Owner |
|---|---|
| Left sidebar | MainMenu |
| Main content | ActivityManager and one selected main Activity |
| Bottom tabs and view | BottomMenu and BottomPanel |
| Loading overlay | ProgressBar |

There is no separate right navigation menu. An activity must not recreate shell navigation, panel containers or loading overlays.

## Files and responsibilities

| Path | Responsibility |
|---|---|
| `run.py` | Local application entry point |
| `app/application_factory.py` | Flask construction, repository attachment, shared endpoints |
| `app/workspace_configuration.py` | Startup registration |
| `app/task_runtime.py` | Background lifecycle, job state, commands, bounded trace entries |
| `app/activities/` | Per-activity Python behavior |
| `app/models/` | Metadata, enums and ORM declarations |
| `app/repositories/` | Database operations, transaction scope, encryption |
| `app/services/` | Public controls and reusable business rules |
| `app/templates/workspace_shell.html` | Shell markup |
| `app/templates/activities/` | Per-activity markup |
| `app/static/js/workspace_shell.js` | Routing, polling, mounting, result delivery |
| `app/static/js/activity_base.js` | Browser lifecycle and listener cleanup |
| `app/static/js/activities/` | Per-activity interaction |
| `app/static/css/workspace.css` | Shared visuals, motion and scoped activity rules |
| `app/static/vendor/` | Bundled Lucide assets and license |
| `docs/` | Jekyll documentation only |

`ActivityDefinition` and `TraceEntry` are dataclasses, not ORM tables. `StoredValue` is an ORM table inheriting `OrmBase`.

## One action through the system

A browser listener sends `shell.run(activityId, payload)`. The factory validates the JSON object and starts a runtime job. The worker binds the service context and calls `on_start()`, `run(payload)`, and cleanup `on_end()`. Polling retrieves the result and commands. The shell calls `onResult(result)` only on the matching selected main view.

Use descriptive modules. Configuration belongs in Store; structured entities belong in models and repositories. Do not introduce a second framework or persistence system for a normal feature.
