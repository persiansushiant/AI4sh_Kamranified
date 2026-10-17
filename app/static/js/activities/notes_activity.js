// Preserve temporary notes in browser shell.memory while switching activities.
// This activity does not persist notes through Store or survive a page reload.
import {Activity} from '../activity_base.js';
export default class NotesActivity extends Activity {
  // Restore temporary notes on mount.
  async onStart(){this.notes_activity_restore();}
  // Read notes from the current shell instance, defaulting to empty text.
  notes_activity_restore(){this.host.querySelector('textarea').value=this.shell.memory.notes||'';}
  // Save notes before inherited cleanup removes listeners.
  async onEnd(){this.notes_activity_save();await super.onEnd();}
  // Copy the current textarea into session-only shell memory.
  notes_activity_save(){this.shell.memory.notes=this.host.querySelector('textarea').value;}
}
