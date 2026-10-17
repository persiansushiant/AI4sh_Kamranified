// Original setup form: restore persisted fields and submit configuration through the shared API.
import {Activity} from '../activity_base.js';
export default class SetupActivity extends Activity {
  // Bind submission first, then restore stored configuration.
  async onStart(){this.setup_activity_bind();await this.setup_activity_load();}
  // Prevent duplicate long-lived listeners by using the base listen() cleanup contract.
  setup_activity_bind(){this.listen(this.host.querySelector('form'),'submit',event=>this.setup_activity_submit(event));}
  // Populate only the three expected fields from the saved configuration.
  async setup_activity_load(){const values=await this.shell.request(`/api/activities/${this.id}/data`);for(const field of ['database_name','username','password'])this.host.querySelector(`[name="${field}"]`).value=values[field]??'';}
  // Prevent browser form navigation and POST the named fields through shell.run().
  async setup_activity_submit(event){event.preventDefault();const payload=Object.fromEntries(new FormData(this.host.querySelector('form')));try{await this.shell.run(this.id,payload);}catch(error){this.onResult({message:error.message});}}
  // Show result text without exposing the form credentials.
  onResult(result){this.host.querySelector('#setupResult').textContent=result?.message||'';}
}
