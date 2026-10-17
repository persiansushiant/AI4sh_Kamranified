// Restore the saved configuration into the masked form and submit through the shared runner.
// Passwords belong only in the form payload; never log them or display them in result messages.
import {Activity} from '../activity_base.js';

export default class ConfigurationSummaryActivity extends Activity {
  // Bind form submission and restore values from the read-only activity data endpoint.
  async onStart() {
    const form = this.host.querySelector('#configurationSummaryForm');
    this.listen(form, 'submit', event => this.configuration_summary_activity_submit(event));
    try {
      const data = await this.shell.request(`/api/activities/${this.id}/data`);
      for (const name of ['database_name', 'username', 'password']) {
        form.elements.namedItem(name).value = data[name] ?? '';
      }
    } catch (error) {
      this.onResult({message: error.message});
    }
  }
  // Prevent normal navigation, use native form validation, and send the named form fields.
  async configuration_summary_activity_submit(event) {
    event.preventDefault();
    const form = this.host.querySelector('#configurationSummaryForm');
    if (!form.reportValidity()) return;
    try {
      await this.shell.run(this.id, Object.fromEntries(new FormData(form)));
    } catch (error) {
      this.onResult({message: error.message});
    }
  }
  // Display plain result text; no HTML is interpreted.
  onResult(result) {
    this.host.querySelector('#configurationSummaryResult').textContent = result?.message ?? '';
  }
}
