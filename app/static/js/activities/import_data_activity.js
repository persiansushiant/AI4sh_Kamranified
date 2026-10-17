// Render import controls from server-provided permissions. aria-disabled preserves
// hover and focus; both the click guard and server permission checks prevent locked actions.
import {Activity} from '../activity_base.js';

// Local SVG paths use the same stroke style as the shared Lucide icons.
const ICON_PATHS = {
  database: ['M4 6c0-4 16-4 16 0s-16 4-16 0', 'M4 6v12c0 4 16 4 16 0V6', 'M4 12c0 4 16 4 16 0'],
  workflow: ['M3 3h6v6H3z', 'M15 15h6v6h-6z', 'M6 9v9h9', 'M15 3h6v6h-6z', 'M9 6h6'],
  trash: ['M3 6h18', 'M9 6V3h6v3', 'M5 6l1 15h12l1-15', 'M10 10v7', 'M14 10v7'],
  wrench: ['M14 6a5 5 0 0 0-6 6L3 17a3 3 0 0 0 4 4l5-5a5 5 0 0 0 6-6l-4 2-2-2 2-4'],
  list: ['M8 6h13', 'M8 12h13', 'M8 18h13', 'M3 6h1', 'M3 12h1', 'M3 18h1'],
  box: ['M12 3l9 5v9l-9 5-9-5V8z', 'M3 8l9 5 9-5', 'M12 13v9'],
  droplet: ['M12 3c-3 5-7 8-7 12a7 7 0 0 0 14 0c0-4-4-7-7-12z'],
  activity: ['M2 12h4l3-9 6 18 3-9h4'],
  layers: ['M12 3l10 6-10 6L2 9z', 'M2 13l10 6 10-6', 'M2 17l10 6 10-6'],
  gamepad: ['M6 7h12l3 11c1 4-4 3-6-1H9c-2 4-7 5-6 1z', 'M6 11v4', 'M4 13h4', 'M16 12h1', 'M18 14h1'],
  table: ['M3 3h18v18H3z', 'M3 9h18', 'M9 9v12'],
  share: ['M8 10l8-5', 'M8 14l8 5', 'M4 9h4v6H4z', 'M16 2h4v6h-4z', 'M16 16h4v6h-4z'],
  clock: ['M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20', 'M12 6v6l4 2'],
  play: ['M7 3l14 9-14 9z'],
};

export default class ImportDataActivity extends Activity {
  // Delegate clicks from the host so newly rendered controls do not need separate listeners.
  // The active flag prevents a late data response from rendering after this view is unmounted.
  async onStart() {
    this.import_data_activity_active = true;
    this.import_data_activity_busy = false;
    this.listen(this.host, 'click', event => {
      const button = event.target.closest('[data-import-action]');
      if (button && this.host.contains(button)) {
        this.import_data_activity_click(button);
      }
    });
    try {
      const state = await this.shell.request(`/api/activities/${this.id}/data`);
      if (this.import_data_activity_active) this.import_data_activity_render(state);
    } catch (error) {
      if (this.import_data_activity_active) this.onResult({message: error.message});
    }
  }

  // Mark the view inactive before releasing inherited event listeners.
  async onEnd() {
    this.import_data_activity_active = false;
    await super.onEnd();
  }

  // Construct local SVG paths with currentColor so CSS determines enabled or locked colors.
  import_data_activity_icon(name) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    for (const [key, value] of Object.entries({viewBox: '0 0 24 24', fill: 'none',
      stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round',
      'stroke-linejoin': 'round', 'aria-hidden': 'true'})) svg.setAttribute(key, value);
    for (const d of ICON_PATHS[name] ?? ICON_PATHS.box) {
      const path = document.createElementNS(ns, 'path');
      path.setAttribute('d', d);
      svg.append(path);
    }
    return svg;
  }

  // Rebuild cards from fresh server state. data-locked controls motion; aria-disabled controls icon colors.
  // textContent is used for labels and messages rather than inserting arbitrary HTML.
  import_data_activity_render(state) {
    this.host.querySelector('[data-import-mode]').textContent = `Import mode: ${state.mode_name}`;
    this.host.querySelectorAll('[data-import-section]').forEach(node => node.replaceChildren());
    for (const action of state.actions) {
      const card = document.createElement('article');
      card.className = 'import-data-card';
      card.dataset.locked = String(!action.enabled);
      card.dataset.action = action.id;
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.importAction = action.id;
      // aria-disabled preserves hover and keyboard focus; click is guarded below and on the server.
      button.setAttribute('aria-disabled', String(!action.enabled));
      button.className = 'import-data-action';
      const icon = document.createElement('span');
      icon.className = 'import-data-icon';
      icon.append(this.import_data_activity_icon(action.icon));
      const title = document.createElement('span');
      title.className = 'import-data-title';
      title.textContent = action.title;
      button.append(icon, title);
      const description = document.createElement('p');
      description.textContent = action.description;
      const status = document.createElement('p');
      status.className = 'import-data-status';
      status.id = `import-data-status-${action.id}`;
      status.textContent = action.enabled ? 'Ready · Implementation pending' : `Locked · ${action.reason}`;
      button.setAttribute('aria-describedby', status.id);
      card.append(button, description, status);
      this.host.querySelector(`[data-import-section="${action.section}"]`).append(card);
    }
  }

  // Ignore duplicate submissions and locked controls. Keep the local busy guard until a result arrives.
  async import_data_activity_click(button) {
    if (this.import_data_activity_busy) return;
    if (button.getAttribute('aria-disabled') === 'true') {
      this.onResult({message: 'This action is unavailable in the current import mode.'});
      return;
    }
    this.import_data_activity_busy = true;
    try {
      await this.shell.run(this.id, {action: button.dataset.importAction});
      // Keep the local guard until the background result arrives.
    } catch (error) {
      this.onResult({message: error.message});
    }
  }

  // Release the local guard, show the outcome, and apply updated permissions if returned.
  onResult(result) {
    this.import_data_activity_busy = false;
    this.host.querySelector('[data-import-result]').textContent = result?.message ?? '';
    if (result?.state) this.import_data_activity_render(result.state);
  }
}
