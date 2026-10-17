// Browser activity lifecycle and automatic event-listener cleanup.
// Each instance scopes UI operations to its host and communicates through the shared shell.
export class Activity {
  // Associate the activity with its string ID, local host element, and shared shell.
  constructor(id, host, shell) { this.id=id; this.host=host; this.shell=shell; this.cleanups=[]; }
  // Optional hook after the UI is mounted.
  async onStart() {}
  // Remove all listeners registered through listen() to prevent stale handlers after view switches.
  async onEnd() { for(const cleanup of this.cleanups) cleanup(); this.cleanups=[]; }
  // Optional hook for completed job output supplied by the shell.
  onResult(result) {}
  // Bind a listener and register its removal; silently ignore missing elements.
  listen(element, event, handler) { if(!element)return; element.addEventListener(event,handler); this.cleanups.push(()=>element.removeEventListener(event,handler)); }
}
