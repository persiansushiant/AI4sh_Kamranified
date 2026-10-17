---
layout: default
title: "Browser lifecycle and UI"
---

# Browser lifecycle and UI


## Browser methods

| Method | Purpose |
|---|---|
| onStart() | Bind events after mount and restore read-only state |
| onEnd() | Release listeners; call super if overridden |
| onResult(result) | Update selected main activity from completed job output |
| listen(element,event,handler) | Register cleanup-aware listener |

Custom methods include their activity ID, e.g. import_data_activity_render. Scope DOM queries to this.host. Use shell.memory for view-switch-only state; use Store for state that survives restart.

shell.request(url) sends a GET. With a payload it sends JSON POST and X-Shell-Request. shell.run(id,payload) acknowledges the start of a background job, not completion. Polling arrives every 350 ms after the previous poll finishes. Only the matching selected main view receives job results.

For pending asynchronous data requests, an activity can keep an active flag and avoid rendering after onEnd. ImportDataActivity already does this. Data and messages should use textContent; use DOM construction rather than injecting untrusted HTML.

## Shared styling

All activities use workspace.css. Add narrowly scoped selectors, not per-activity stylesheets or a second design system. Shared short motion durations are 140/200 ms with cubic-bezier(.2,.8,.2,1). Respect prefers-reduced-motion.

The supplied CSS contains earlier import style blocks plus later overrides. This documentation does not remove or consolidate them. CSS order matters; final icon rules use button aria-disabled and important declarations.

Enabled import icons inherit --action-color and --action-background from data-import-action. Locked icons are neutral gray. Card data-locked drives hover/focus movement. Native disabled is not set on these buttons, preserving focus and hover; therefore click and server guards are essential.

## Icons

The shell and Log use locally bundled Lucide. Pass lowercase hyphenated menu icon names such as settings, database, brain, terminal or file-text. Unknown menu names fall back to circle-help. Keep the bundled license.

ImportDataActivity currently constructs SVGs from its own ICON_PATHS table using the Lucide stroke style. These are custom paths, not calls to the bundled Lucide library. Some unused paths remain from removed Workspace cards. Reusing true Lucide for this view is a future change, not something this guide claims is already implemented.

## Shared HTTP endpoints

| Endpoint | Behavior |
|---|---|
| GET / | Shell markup |
| GET /api/state | Activities, job, loading, commands and traces |
| GET /api/activities/&lt;id&gt;/ui | Activity fragment |
| GET /api/activities/&lt;id&gt;/data | Read-only Python load(), no-store |
| POST /api/activities/&lt;id&gt;/run | Validate JSON object and start job, HTTP 202 |

Unavailable activities return 404; malformed action payloads return 400; concurrent action attempts return 409. A missing application POST header returns 403. This header does not provide login or authentication.
