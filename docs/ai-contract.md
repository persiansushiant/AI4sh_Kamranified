---
layout: default
title: "AI implementation contract"
---

# AI implementation contract


Copy this contract when asking another assistant to add a feature. Attach current source files as well as the relevant docs. Source remains authoritative.

```text
Implement the feature below in the existing AI4SH backbone.
Inspect current source before editing; do not invent public APIs.
Preserve Flask, plain JavaScript ES modules, shared CSS, and existing services.
Use the three-file activity convention and globally unique activity IDs.
Keep Python behavior, metadata/models, repositories, services, markup and browser handlers separate.
Use Store for configuration and flags; use repositories and ORM models for domain entities.
Keep load() read-only. Perform operations through the normal background activity lifecycle.
Use cleanup-aware browser listeners and host-scoped queries.
Validate permissions and payloads on the server, not only in the UI.
Advance modes only after real successful operations; placeholders must not claim completion.
Keep workspace.mode separate from import_data.mode.
Use Trace with existing sections and safe messages; never log secrets or unsafe exception text.
Use ProgressBar.start/end with finally cleanup, without percentage updates.
Keep all comments, docstrings and UI text English.
Do not change the framework, introduce disabled menu items without instruction,
or add unrelated dependencies or unsupported APIs.
If a shared API needs extending, state the extension and verify it explicitly.
Update the relevant documentation when behavior changes.
Report files changed, verification actually performed, and remaining limitations.

Feature:
Activity ID and class:
Placement (main/bottom):
Numeric menu ID:
Workspace modes where visible:
Import modes/action permissions, if relevant:
Persistent keys/entities:
Input and validation:
Successful output and state transition:
Failure behavior:
```

For a comment-only task, add: "Only insert standalone comments. Preserve every original source line and archive entry. Do not add docstrings, rename, reformat, fix or remove code. Verify exact original-line recovery and semantic equality where applicable."
