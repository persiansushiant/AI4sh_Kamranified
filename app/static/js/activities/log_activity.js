// Render Trace entries with persistent section and status filters.
// Preferences are stored for this browser and application origin.
import { Activity } from '../activity_base.js';

const TRACE_ICONS = {
  info: 'info',
  success: 'circle-check',
  warning: 'triangle-alert',
  error: 'circle-x',
};

export default class LogActivity extends Activity {
  // Restore preferences before rendering the first view.
  async onStart() {
    this.entries = [];
    this.signature = '';

    await this.log_activity_load_filters();
    this.log_activity_bind();
    this.log_activity_render([]);
  }

  // Load available filters and restore valid saved selections.
  async log_activity_load_filters() {
    const options = await this.shell.request(
      '/api/activities/log/data'
    );

    const filters = [
      ['traceSection', options.sections],
      ['traceStatus', options.statuses],
    ];

    for (const [id, values] of filters) {
      const select = this.host.querySelector('#' + id);

      for (const value of values) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent =
          value.charAt(0).toUpperCase() + value.slice(1);

        select.append(option);
      }

      // Keep session memory as a fallback if storage is blocked.
      let saved = this.shell.memory[id] || 'all';

      try {
        saved =
          localStorage.getItem('ai4sh.log.' + id) ?? saved;
      } catch {
        // Filtering remains available without browser storage.
      }

      // Fall back to All if an older saved value is no longer valid.
      select.value = ['all', ...values].includes(saved)
        ? saved
        : 'all';

      this.shell.memory[id] = select.value;
    }
  }

  // Save each selection immediately and apply it to existing entries.
  log_activity_bind() {
    for (const id of ['traceSection', 'traceStatus']) {
      const select = this.host.querySelector('#' + id);

      this.listen(select, 'change', () => {
        const value = select.value;

        this.shell.memory[id] = value;

        try {
          localStorage.setItem('ai4sh.log.' + id, value);
        } catch {
          // A storage failure must not interrupt filtering.
        }

        this.log_activity_render(this.entries);
      });
    }
  }

  // Skip unchanged output and preserve the user's scroll position.
  log_activity_render(entries) {
    this.entries = entries;

    const section =
      this.host.querySelector('#traceSection').value;

    const status =
      this.host.querySelector('#traceStatus').value;

    const signature = JSON.stringify([
      entries.at(-1)?.id,
      entries.length,
      section,
      status,
    ]);

    if (this.signature === signature) {
      return;
    }

    this.signature = signature;

    const filtered = entries.filter(
      (entry) =>
        (section === 'all' || entry.section === section) &&
        (status === 'all' || entry.status === status)
    );

    const rows = this.host.querySelector('#traceRows');

    const nearBottom =
      this.host.scrollHeight -
        this.host.scrollTop -
        this.host.clientHeight <
      48;

    rows.replaceChildren(
      ...filtered.map((entry) => this.log_activity_row(entry))
    );

    this.host.querySelector('#traceCount').textContent =
      filtered.length + ' / ' + entries.length;

    const empty = this.host.querySelector('#traceEmpty');

    empty.hidden = filtered.length > 0;
    empty.textContent = entries.length
      ? 'No messages match these filters.'
      : 'No trace messages yet.';

    window.lucide.createIcons({
      attrs: {
        width: 15,
        height: 15,
        'stroke-width': 1.8,
      },
    });

    if (nearBottom) {
      this.host.scrollTop = this.host.scrollHeight;
    }
  }

  // Build rows using textContent so messages remain plain text.
  log_activity_row(entry) {
    const row = document.createElement('div');
    row.className = 'trace-row trace-' + entry.status;

    const indicator = document.createElement('span');
    indicator.className = 'trace-indicator';
    indicator.title = entry.status;

    const icon = document.createElement('span');
    icon.dataset.lucide =
      TRACE_ICONS[entry.status] || 'info';

    icon.setAttribute('aria-hidden', 'true');
    indicator.append(icon);

    const status = document.createElement('span');
    status.className = 'trace-status';
    status.textContent = entry.status;

    const time = document.createElement('time');
    time.dateTime = entry.time;
    time.textContent =
      new Date(entry.time).toLocaleTimeString();

    const section = document.createElement('span');
    section.className = 'trace-section';
    section.textContent = entry.section;

    const message = document.createElement('span');
    message.className = 'trace-message';
    message.textContent = entry.message;

    row.append(
      indicator,
      time,
      section,
      status,
      message
    );

    return row;
  }
}