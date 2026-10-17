// Shared shell: mount activity views, poll runtime state, render menus, and apply commands.
// Main and bottom activities have separate lifecycles. Polling delivers completed jobs
// only to the currently selected main activity, not to every registered view.
const element=id=>document.getElementById(id);
class Shell {
  // Initialize independent view-switch guards, browser memory, and polling cursors.
  constructor(){this.bottomCurrent=null;this.bottomSwitching=false;this.current=null;this.busy=false;this.switching=false;this.memory={};this.seenJob=null;this.pendingRun=false;this.commandCursor=0;this.poppedCommands=new Set();}
  // GET when payload is undefined; otherwise POST JSON with the application header.
  // This request header is a local guard, not an authentication mechanism.
  async request(url,payload){const response=await fetch(url,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Shell-Request':'1'},body:JSON.stringify(payload)});if(!response.ok){let message='Request failed';try{message=(await response.json()).error||message;}catch{}throw Error(message);}return response.headers.get('content-type')?.includes('application/json')?response.json():response.text();}
  // Fetch HTML and import the activity module concurrently, then mount and start the view.
  async mount(id,host){const [html,module]=await Promise.all([this.request(`/api/activities/${id}/ui`),import(`/static/js/activities/${id}_activity.js`)]);host.innerHTML=html;const activity=new module.default(id,host,this);await activity.onStart();return activity;}
  // Switch the main view after cleaning up the previous activity; ignore busy or redundant requests.
  async open(id){if(this.busy||this.switching||this.current?.id===id)return;this.switching=true;try{if(this.current)await this.current.onEnd();this.current=await this.mount(id,element('content'));this.renderMenu();}catch(error){element('content').textContent=error.message;this.current=null;}finally{this.switching=false;}}
  // Resolve a bundled Lucide icon name and fall back to circle-help for unknown names.
  iconName(name){const key=String(name).replace(/(^|-)([a-z])/g,(_,dash,letter)=>letter.toUpperCase());return window.lucide.icons[key]?name:"circle-help";}
  // Rebuild sidebar only when metadata or selection changes, preserving hover during polling.
  renderMenu(){const signature=JSON.stringify([this.activities.filter(a=>a.placement==='main'),this.current?.id]);if(signature===this.mainMenuSignature)return;this.mainMenuSignature=signature;element('navigation').replaceChildren(...this.activities.filter(a=>a.placement==='main').map(a=>{const button=document.createElement('button');const icon=document.createElement('span');icon.dataset.lucide=this.iconName(a.icon);icon.setAttribute("aria-hidden","true");const label=document.createElement('span');label.textContent=a.title;button.append(icon,label);button.disabled=!a.enabled;button.title=a.reason;button.classList.toggle('active',a.id===this.current?.id);button.onclick=()=>this.open(a.id);return button;}));window.lucide.createIcons({attrs:{width:20,height:20,"stroke-width":1.8}});}
  // Apply the same signature-based rendering to independent bottom-panel tabs.
  renderBottomMenu(){const signature=JSON.stringify([this.activities.filter(a=>a.placement==='bottom'),this.bottomCurrent?.id]);if(signature===this.bottomMenuSignature)return;this.bottomMenuSignature=signature;element('bottomNavigation').replaceChildren(...this.activities.filter(a=>a.placement==='bottom').map(a=>{const button=document.createElement('button');const icon=document.createElement('span');icon.dataset.lucide=this.iconName(a.icon);icon.setAttribute('aria-hidden','true');const label=document.createElement('span');label.textContent=a.title;button.append(icon,label);button.disabled=!a.enabled;button.title=a.reason;button.classList.toggle('active',a.id===this.bottomCurrent?.id);button.onclick=()=>this.openBottom(a.id);return button;}));window.lucide.createIcons({attrs:{width:18,height:18,'stroke-width':1.8}});}
  // Switch the selected bottom activity without revealing a closed panel.
  async openBottom(id,allowBusy=false){if(!id||(this.busy&&!allowBusy)||this.bottomSwitching||this.bottomCurrent?.id===id)return;this.bottomSwitching=true;try{if(this.bottomCurrent)await this.bottomCurrent.onEnd();this.bottomCurrent=null;this.bottomCurrent=await this.mount(id,element('logContent'));this.renderBottomMenu();}catch(error){element('logContent').textContent=error.message;}finally{this.bottomSwitching=false;}}
  // Pop commands bypass the loading gate without consuming earlier deferred commands.
  // Remember handled IDs so polling never repeatedly steals the selected tab.
  async applyBottomPops(commands){
    const visibleIds=new Set(commands.map(command=>command.id));
    for(const id of this.poppedCommands)if(!visibleIds.has(id))this.poppedCommands.delete(id);
    for(const command of commands){
      if(command.id<=this.commandCursor||command.kind!=='bottom.pop'||this.poppedCommands.has(command.id))continue;
      const activity=this.activities.find(item=>item.id===command.value&&item.placement==='bottom'&&item.enabled);
      if(!activity){this.poppedCommands.add(command.id);continue;}
      if(this.bottomSwitching)continue;
      this.showLog(true);
      await this.openBottom(command.value,true);
      if(this.bottomCurrent?.id===command.value)this.poppedCommands.add(command.id);
    }
  }
  // Show loading and make the application inert; this does not start a Python job.
  start(message='Starting…'){this.busy=true;element('application').inert=true;element('progressOverlay').hidden=false;element('progressMessage').textContent=message;element('progressOverlay').tabIndex=-1;element('progressOverlay').focus();}
  // Hide loading and restore interaction; this does not cancel background execution.
  end(){this.busy=false;element('application').inert=false;element('progressOverlay').hidden=true;element('content').focus();}
  // Submit a background action. The response acknowledges job start; final results arrive via polling.
  async run(id,payload){if(this.busy)return;this.pendingRun=true;try{const result=await this.request(`/api/activities/${id}/run`,payload);this.seenJob=null;return result;}catch(error){this.end();throw error;}finally{this.pendingRun=false;}}
  // Fetch runtime state, synchronize loading, deliver main-view results, and process unseen commands.
  // Ordinary commands are deferred while loading; bottom.pop is handled immediately.
  async refresh(){const state=await this.request('/api/state');this.activities=state.activities;this.renderMenu();this.renderBottomMenu();if(this.bottomCurrent?.id==='log')this.bottomCurrent.log_activity_render(state.logs);await this.applyBottomPops(state.commands);const job=state.job;const progress=state.progress;if(progress.active){if(!this.busy)this.start();element('progressMessage').textContent=progress.text;}else if(this.busy)this.end();element('status').textContent=job?.status||'Ready';if(job&&job.status!=='running'&&this.seenJob!==job.id){this.seenJob=job.id;if(this.current?.id===job.activity)this.current.onResult(job.result);if(job.status==='failed')this.showLog(true);}for(const command of state.commands){if(command.id<=this.commandCursor)continue;if(this.busy)break;this.commandCursor=command.id;if(command.kind==='panel.open')this.showLog(true);if(command.kind==='panel.close')this.showLog(false);if(command.kind==='panel.height')this.setPanelHeight(command.value);if(command.kind==='activity.open')await this.open(command.value);if(command.kind==='bottom.open')await this.openBottom(command.value);if(command.kind==='bottom.reload'&&this.bottomCurrent?.id===command.value)await this.bottomCurrent.onResult();}if(this.current&&!this.activities.some(a=>a.id===this.current.id&&a.enabled))await this.open(this.activities.find(a=>a.placement==='main'&&a.enabled)?.id);await this.reconcileBottom();}
  // Unmount removed or disabled bottom views and choose an enabled fallback when available.
  async reconcileBottom(){if(this.bottomCurrent&&!this.activities.some(a=>a.id===this.bottomCurrent.id&&a.placement==='bottom'&&a.enabled)){await this.bottomCurrent.onEnd();this.bottomCurrent=null;element('logContent').replaceChildren();}if(!this.bottomCurrent&&!this.busy)await this.openBottom(this.activities.find(a=>a.placement==='bottom'&&a.enabled)?.id);this.renderBottomMenu();}
  // Clamp height to 90 pixels through 65 percent of the viewport and save the browser preference.
  setPanelHeight(height){const value=Math.min(window.innerHeight*.65,Math.max(90,height));element("bottomPanel").style.height=value+"px";try{localStorage.setItem("shell.logHeight",String(value));}catch{}}
  // Toggle panel visibility and persist the browser preference when storage is available.
  showLog(open){element('bottomPanel').hidden=!open;try{localStorage.setItem('shell.logOpen',String(open));}catch{}}
  // Restore panel preferences and bind pointer dragging plus keyboard resizing.
  bindPanel(){const panel=element('bottomPanel');let height=220,open=true;try{height=Number(localStorage.getItem('shell.logHeight'))||220;open=localStorage.getItem('shell.logOpen')!=='false';}catch{}panel.style.height=Math.min(window.innerHeight*.65,Math.max(90,height))+'px';this.showLog(open);element('logToggle').onclick=()=>this.showLog(panel.hidden);element('logOpen').onclick=()=>this.showLog(true);element('logClose').onclick=()=>this.showLog(false);const handle=element('resizeHandle');const resize=value=>{const next=Math.min(window.innerHeight*.65,Math.max(90,value));panel.style.height=next+'px';handle.setAttribute('aria-valuenow',String(Math.round(next)));try{localStorage.setItem('shell.logHeight',String(next));}catch{}};handle.onpointerdown=event=>{handle.setPointerCapture(event.pointerId);const startY=event.clientY,startHeight=panel.offsetHeight;handle.onpointermove=move=>resize(startHeight+startY-move.clientY);handle.onpointerup=()=>{handle.onpointermove=null;};handle.onpointercancel=()=>{handle.onpointermove=null;};};handle.onkeydown=event=>{if(['ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();resize(panel.offsetHeight+(event.key==='ArrowUp'?20:-20));}};}
  // Initialize the shell and poll every 350 ms after each completed poll, retrying on connection errors.
  async boot(){this.bindPanel();await this.refresh();if(!this.busy)await this.open(this.activities.find(a=>a.placement==='main'&&a.enabled)?.id);const poll=async()=>{try{await this.refresh();if(!this.current&&!this.busy)await this.open(this.activities.find(a=>a.placement==='main'&&a.enabled)?.id);}catch(error){element('status').textContent='Connection lost · retrying';if(this.busy)element('progressMessage').textContent='Connection lost. Waiting to confirm task completion…';}finally{setTimeout(poll,350);}};setTimeout(poll,350);}
}
const shell=new Shell();shell.boot().catch(error=>{element('content').textContent=error.message;});
// Console API for learning: shell.start(), shell.end(), shell.open('setup').
window.shell=shell;
