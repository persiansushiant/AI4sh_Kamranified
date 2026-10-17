---
layout: default
title: "Start here"
---

# Start here


This documentation describes the supplied AI4SH backbone source snapshot, dated **8 October 2026**. Later source changes take precedence over this guide.

The application is a local, single-user Flask workspace. Python owns validation and operations; the browser owns interaction; shared services own navigation, loading, persistence and tracing.

## Choose a path

| Goal | Read |
|---|---|
| Run the project | [Getting started](getting-started.html) |
| Understand file responsibilities | [Architecture](architecture.html) |
| Add a page with an operation | [Add an activity](activities.html) |
| Add a sidebar or bottom tab | [Menus and panels](menus.html) |
| Change available pages or buttons | [Modes and permissions](modes.html) |
| Save settings and flags | [Persistence and ORM](persistence.html) |
| Report steps and errors | [Trace and loading](trace-loading.html) |
| Change icons, hover or lifecycle | [Browser and UI](browser-ui.html) |
| Verify a change | [Validation](validation.html) |
| Ask another AI to implement a feature | [AI implementation contract](ai-contract.html) |
| Publish code and these docs | [GitHub and Jekyll](github-publishing.html) |

## Current implementation limits

Import data handlers return `implemented: false`; they do not create or copy a PostgreSQL database. The machine-learning page is a placeholder. `MlActivity` is a separate simulated training demo. Saving connection settings does not establish a PostgreSQL connection.

GitHub Pages publishes this static documentation. Users still run Flask locally or on a separately configured Python host.
