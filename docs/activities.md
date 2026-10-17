---
layout: default
title: "Add an activity"
---

# Add an activity


## Naming contract

For ID `dataset_label` create exactly:

- `app/activities/dataset_label_activity.py`
- `app/templates/activities/dataset_label_activity_ui.html`
- `app/static/js/activities/dataset_label_activity.js`

Python and JS class: `DatasetLabelActivity`. Python constructors have no required arguments. Browser modules default-export their class. String IDs must be unique across main and bottom menus.

## Python implementation

```python
from .activity_base import Activity
from ..services.persistent_store import Store
from ..services.execution_trace import Trace
from ..services.progress_bar import ProgressBar

class DatasetLabelActivity(Activity):
    def __init__(self):
        super().__init__("dataset_label")

    def load(self):
        return {"label": Store.get("dataset.label", "")}

    def run(self, payload):
        label = payload.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Dataset label is required.")
        if len(label) > 200:
            raise ValueError("Dataset label is too long.")
        ProgressBar.start("Saving dataset label…")
        try:
            Store.set("dataset.label", label.strip())
            Trace.success("process", "Dataset label saved")
            return {"message": "Dataset label saved."}
        finally:
            ProgressBar.end()
```

`load()` is read-only and returns JSON-serializable UI data. Opening a page does not execute Python `run()` or `on_start()`. `on_start()` runs before background execution; `on_end()` is attempted after success or failure. Neither hook is a page-mount hook.

## HTML implementation

```html
<p class="eyebrow">DATASET</p>
<h1>Dataset label</h1>
<article>
  <form id="datasetLabelForm">
    <label for="datasetLabel">Label</label>
    <input id="datasetLabel" name="label" required maxlength="200">
    <button type="submit">Save label</button>
  </form>
  <p id="datasetLabelResult" role="status" aria-live="polite"></p>
</article>
```

This is a fragment: do not extend a different base template or add another complete HTML document.

## Browser implementation

```javascript
import {Activity} from '../activity_base.js';

export default class DatasetLabelActivity extends Activity {
  async onStart() {
    const form = this.host.querySelector('#datasetLabelForm');
    this.listen(form, 'submit', event =>
      this.dataset_label_activity_submit(event));
    try {
      const data = await this.shell.request(`/api/activities/${this.id}/data`);
      form.elements.namedItem('label').value = data.label ?? '';
    } catch (error) {
      this.onResult({message: error.message});
    }
  }

  async dataset_label_activity_submit(event) {
    event.preventDefault();
    const form = this.host.querySelector('#datasetLabelForm');
    if (!form.reportValidity()) return;
    try {
      await this.shell.run(this.id, Object.fromEntries(new FormData(form)));
    } catch (error) {
      this.onResult({message: error.message});
    }
  }

  onResult(result) {
    this.host.querySelector('#datasetLabelResult').textContent = result?.message ?? '';
  }
}
```

Scope queries to `this.host`; use `this.listen()` for cleanup. Custom browser method names include the activity ID. If overriding `onEnd()`, call `await super.onEnd()`.

## Registration

In `app/workspace_configuration.py`:

```python
from .activities.dataset_label_activity import DatasetLabelActivity
from .services.main_menu import MainMenu

# Add inside configure(), after register_mode_activities().
MainMenu.add(30, "Dataset label", DatasetLabelActivity, "file-text")
```

30 is an example: verify it is free. This example makes the new item visible in every workspace mode. To show it only in selected modes, add its registration to the relevant branches of `register_mode_activities()` and include its reserved ID in that function's removal set.

No new HTTP route is necessary for standard load/run behavior. Verify loading, validation, persistence after restart, result delivery and error cleanup.
