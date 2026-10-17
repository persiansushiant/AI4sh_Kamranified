// Bind overview navigation links to the shared shell using string activity IDs.
import {Activity} from '../activity_base.js';
export default class HomeActivity extends Activity {
  // Register navigation handlers on mount.
  async onStart(){this.home_activity_bind();}
  // Use cleanup-aware listeners for each data-open navigation target.
  home_activity_bind(){this.host.querySelectorAll('[data-open]').forEach(button=>this.listen(button,'click',()=>this.shell.open(button.dataset.open)));}
}
