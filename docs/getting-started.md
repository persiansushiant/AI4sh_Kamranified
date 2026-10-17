---
layout: default
title: "Getting started"
---

# Getting started


## Required project files

Use the complete existing project with `run.py`, `app/`, and its actual dependency manifest. This documentation ZIP is an overlay and is not a runnable application distribution.

The supplied source uses Flask, SQLAlchemy and cryptography. Keep dependency versions in your maintained manifest; this package does not invent versions or replace it.

## Windows execution

From the folder containing `run.py`:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Open `http://127.0.0.1:5000/`. In PyCharm, select `run.py` as the script and the project root as the working directory. Do not execute files inside `app` directly: relative imports require package context.

If the optional launcher is present, double-click `Start-AI4SH.bat`. It creates `.venv`, installs dependencies when its manifest fingerprint changes, starts `run.py`, and opens the browser after HTTP readiness. Python must already be available. Keep the server window open; Ctrl+C stops it.

## First use

1. Workspace mode 0 exposes Configuration.
2. Enter database name, database username, and a masked password of at least six characters.
3. Save. Configuration is encrypted in local SQLite; workspace mode advances to 1 and Import data opens.
4. Import controls restore their own independent mode. Placeholder clicks currently report that implementation is pending.

Configuration survives restart. Runtime menus and traces do not: menus are rebuilt from saved mode, while logs start empty.
