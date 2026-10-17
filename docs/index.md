---
layout: default
title: Home
nav_order: 1
---

# A clear foundation.
One guide to build on.


This documentation describes the supplied AI4SH backbone source snapshot, dated **8 October 2026**. Later source changes take precedence over this guide.

The application is a local, single-user Flask workspace. Python owns validation and operations; the browser owns interaction; shared services own navigation, loading, persistence and tracing.

<div class="hero">
<div class="badge">THE AI4SH APPLICATION BACKBONE</div>
<h2>From first run to your next feature.</h2>
<p>Understand the architecture, follow the extension recipes, and keep every new feature consistent.</p>
<a href="getting-started.html">Get started →</a><a class="secondary" href="architecture.html">Explore the architecture ↗</a>
</div>

<div class="cards">
<a class="card" href="activities.html"><span class="number">01 / BUILD</span><b>Add an activity →</b><small>Python, templates and browser lifecycle.</small></a>
<a class="card" href="menus.html"><span class="number">02 / CONNECT</span><b>Menus & panels →</b><small>Navigation and the shared bottom panel.</small></a>
<a class="card" href="persistence.html"><span class="number">03 / REMEMBER</span><b>Settings & state →</b><small>Configuration, flags and persistence.</small></a>
<a class="card" href="validation.html"><span class="number">04 / VERIFY</span><b>Validate a change →</b><small>Checks and troubleshooting recipes.</small></a>
</div>

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
