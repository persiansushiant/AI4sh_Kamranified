from app import create_app
from app.services.workspace_context import bind, unbind
from app.services.bottom_menu import BottomMenu
from app.activities.configuration_summary_activity import ConfigurationSummaryActivity
from test_persistent_store import finish, H

def test_bottom_menu_add_remove_and_separate_ids(tmp_path):
 a=create_app(tmp_path/'state.sqlite3');s=a.extensions['runtime'];t=bind(s)
 try:
  assert s.menu[1]=='setup' and s.bottom_menu[1]=='log'
  BottomMenu.add(2,'Summary',ConfigurationSummaryActivity,'database')
  assert BottomMenu.contains(2)
  assert s.registry['configuration_summary'].metadata()['placement']=='bottom'
  BottomMenu.remove(2)
  assert not BottomMenu.contains(2)
  assert 'configuration_summary' not in s.registry
 finally:unbind(t)

def test_save_reveals_bottom_activity_and_restores_on_restart(tmp_path):
 p=tmp_path/'state.sqlite3';a=create_app(p);c=a.test_client()
 assert 'configuration_summary' not in a.extensions['runtime'].registry
 for _ in range(2):
  c.post('/api/activities/setup/run',json={'database_name':'soil','username':'tester','password':'secret'},headers=H)
  assert finish(c)['status']=='succeeded'
 state=c.get('/api/state').get_json()
 assert len([x for x in state['activities'] if x['id']=='configuration_summary'])==1
 summary=c.get('/api/activities/configuration_summary/data').get_json()
 assert summary=={'database_name':'soil','username':'tester','completed':True}
 assert 'secret' not in str(summary)
 restarted=create_app(p)
 assert 'configuration_summary' in restarted.extensions['runtime'].registry
