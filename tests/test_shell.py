import time
import pytest
from app import create_app as application_factory
import tempfile
from pathlib import Path

def create_app():
 return application_factory(Path(tempfile.mkdtemp()) / "test.sqlite3")
from app.services.workspace_context import bind, unbind
from app.services.main_menu import MainMenu
from app.services.progress_bar import ProgressBar
from app.services.bottom_panel import BottomPanel
from app.services.activity_manager import ActivityManager
from app.activities.notes_activity import NotesActivity
from app.activities.activity_base import Activity
H={'X-Shell-Request':'1'}
def wait(c):
 for _ in range(150):
  s=c.get('/api/state').get_json()
  if s['job'] and s['job']['status']!='running':return s
  time.sleep(.03)
 raise AssertionError('Task did not finish')
def test_menu():
 s=create_app().extensions['runtime'];t=bind(s)
 try:
  MainMenu.add(10,'Test',NotesActivity,'notebook-pen');assert s.menu[10]=='notes'
  MainMenu.disable(10);assert not s.registry['notes'].enabled
  MainMenu.enable(10);assert s.registry['notes'].enabled
  with pytest.raises(ValueError):MainMenu.add(10,'Dup',NotesActivity,'x')
  MainMenu.remove(10);assert 'notes' not in s.registry
 finally:unbind(t)
def test_progress_commands():
 s=create_app().extensions['runtime'];t=bind(s)
 try:
  ProgressBar.start();assert s.snapshot()['progress']['active']
  assert set(s.snapshot()['progress'])=={'active','text'}
  assert not hasattr(ProgressBar,'update')
  ProgressBar.end();assert not s.snapshot()['progress']['active']
  BottomPanel.open();BottomPanel.set_height(300);BottomPanel.close();ActivityManager.open(2)
  assert [c['kind'] for c in s.commands]==['panel.open','panel.height','panel.close','activity.open']
 finally:unbind(t)
def test_success_lock():
 c=create_app().test_client()
 assert c.post('/api/activities/ml/run',json={},headers=H).status_code==202
 assert c.post('/api/activities/ml/run',json={},headers=H).status_code==409
 s=wait(c);assert s['job']['status']=='succeeded';assert not s['progress']['active']
def test_forgotten_end_cleanup():
 a=create_app();c=a.test_client();s=a.extensions['runtime']
 class BrokenActivity(Activity):
  def __init__(self):super().__init__('broken')
  def run(self,payload):ProgressBar.start();raise ValueError('Intentional failure')
 s.registry['broken']=BrokenActivity()
 c.post('/api/activities/broken/run',json={},headers=H)
 state=wait(c);assert state['job']['status']=='failed';assert not state['progress']['active']
 assert any('broken: on_end' in l['message'] for l in state['logs'])
def test_menu_demo():
 c=create_app().test_client()
 for action in ['notes/add','notes/remove']:
  assert c.post('/api/activities/menu/run',json={'action':action},headers=H).status_code==202
  assert wait(c)['job']['status']=='succeeded'
 assert c.get('/api/activities/notes/ui').status_code==404
 assert c.get('/api/activities/ml/ui').status_code==200
def test_validation():
 c=create_app().test_client()
 assert c.post('/api/activities/setup/run',json={}).status_code==403
 assert c.post('/api/activities/setup/run',json=[],headers=H).status_code==400
 assert c.get('/api/activities/ml/ui').status_code==200

def test_loading_markup_and_local_icons():
 c=create_app().test_client()
 html=c.get('/').get_data(as_text=True)
 assert 'loading-spinner' in html
 assert '<progress' not in html and 'progressPercent' not in html
 assert '/static/vendor/lucide.min.js' in html
 assert c.get('/static/vendor/lucide.min.js').status_code==200
 state=c.get('/api/state').get_json()
 assert [a['icon'] for a in state['activities'] if a['placement']=='main']==['settings','layout-dashboard','brain','sliders-horizontal']


def test_all_initial_menu_items_are_enabled():
 state=create_app().test_client().get("/api/state").get_json()
 assert all(a["enabled"] for a in state["activities"])
