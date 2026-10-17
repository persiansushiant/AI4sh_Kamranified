// Run the simulated training demo with either a normal or intentional failure payload.
import {Activity} from '../activity_base.js';
export default class MlActivity extends Activity {
  // Bind both training demo paths.
  async onStart(){this.ml_activity_bind();}
  // Use separate buttons for normal execution and intentional failure.
  ml_activity_bind(){this.listen(this.host.querySelector('#mlRun'),'click',()=>this.ml_activity_run(false));this.listen(this.host.querySelector('#mlFail'),'click',()=>this.ml_activity_run(true));}
  // Send the fail flag to Python; actual job completion is reported by polling.
  async ml_activity_run(fail){try{await this.shell.run(this.id,{fail});}catch(error){this.onResult({message:error.message});}}
  // Render the demo outcome as plain text.
  onResult(result){this.host.querySelector('#mlResult').textContent=result?.message||'';}
}
