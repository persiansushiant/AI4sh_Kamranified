---
layout: default
title: "Menus and bottom panel"
---

# Menus and bottom panel


## Public controls

```python
from app.services.main_menu import MainMenu
from app.services.bottom_menu import BottomMenu
from app.services.activity_manager import ActivityManager
from app.services.bottom_panel import BottomPanel
```

Use relative imports from inside activities. These controls require a bound runtime: configuration, activity load, or the worker lifecycle supplies it.

| Goal | Call |
|---|---|
| Register sidebar item | `MainMenu.add(30, "Dataset", DatasetLabelActivity, "file-text")` |
| Remove sidebar item | `MainMenu.remove(30)` |
| Open sidebar item | `ActivityManager.open(30)` |
| Disable / enable sidebar | `MainMenu.disable(30, "Complete setup first")` / `MainMenu.enable(30)` |
| Register bottom tab | `BottomMenu.add(90, "Log", LogActivity, "terminal")` |
| Bottom membership | `BottomMenu.contains(90)` |
| Select / reload bottom view | `BottomMenu.open(90)` |
| Remove bottom item | `BottomMenu.remove(90)` |
| Disable / enable bottom | `BottomMenu.disable(90, "Unavailable")` / `BottomMenu.enable(90)` |
| Show / hide panel | `BottomPanel.open()` / `BottomPanel.close()` |
| Set panel height | `BottomPanel.set_height(300)` |

Pass the imported class, never a string filename. Numeric IDs are separate per menu, but activity string IDs are global. Registering the same string ID in both menus raises an error. Removal of a missing numeric ID is harmless; opening a missing ID fails. MainMenu has no `contains()` API in this snapshot.

## Add Log to startup

The supplied `configure()` calls only `register_mode_activities()`; it does not register Log. To make Trace visible in the bottom panel, explicitly add this example inside configure(), using a free bottom ID:

```python
from .activities.log_activity import LogActivity
from .services.bottom_menu import BottomMenu

# Inside configure(), after staged sidebar registration:
BottomMenu.add(90, "Log", LogActivity, "terminal")
```

To reveal it after an action:

```python
BottomMenu.open(90)
BottomPanel.open()
```

BottomMenu.open selects and queues reload but does not reveal a hidden panel. Generic background result delivery is for main views; a new bottom activity that runs tasks needs an explicitly designed result/reload contract. Do not assume onResult receives every bottom task's result.

## Persistence and ordering

Menu registrations are runtime state, not Store records. Persist the condition, rebuild at startup, and update runtime menus only after successful work. The browser sees commands on polling, not synchronously during Python calls. Maintain an enabled main fallback.

Panel height is clamped to at least 90 pixels and at most 65 percent of the browser viewport. Height and visibility are saved in localStorage. Dragging and ArrowUp/ArrowDown resizing are supported.
