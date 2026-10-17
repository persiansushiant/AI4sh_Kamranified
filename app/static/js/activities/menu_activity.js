// Translate menu demo buttons into named Python actions through the shared activity runner.
import {Activity} from '../activity_base.js';
export default class MenuActivity extends Activity {
  // Bind the command buttons on mount.
  async onStart(){this.menu_activity_bind();}
  // Read each action ID from data-menu and register a cleanup-aware listener.
  menu_activity_bind(){this.host.querySelectorAll('[data-menu]').forEach(button=>this.listen(button,'click',()=>this.menu_activity_command(button.dataset.menu)));}
  // Submit the selected action; surface request errors in the result area.
  async menu_activity_command(action){try{await this.shell.run(this.id,{action});}catch(error){this.onResult({message:error.message});}}
  // Render the result as text.
  onResult(result){this.host.querySelector('#menuResult').textContent=result?.message||'';}
}
