import time
import pytest
from app import create_app
from app.repositories.key_value_repository import KeyValueRepository
from app.services.workspace_context import bind, unbind
from app.services.persistent_store import Store

H={'X-Shell-Request':'1'}
def finish(client):
 for _ in range(100):
  state=client.get('/api/state').get_json()
  if state['job']['status']!='running':return state['job']
  time.sleep(.02)
 raise AssertionError('Task never finished')

def test_form_persists_across_restart(tmp_path):
 path=tmp_path/'settings.sqlite3'
 a=create_app(path);c=a.test_client()
 assert c.get('/api/activities/setup/data').get_json()=={}
 assert c.get('/api/state').get_json()['activities'][0]['id']=='setup'
 values={'database_name':'soil','username':'researcher','password':'test-secret-123'}
 assert c.post('/api/activities/setup/run',json=values,headers=H).status_code==202
 assert finish(c)['status']=='succeeded'
 assert c.get('/api/activities/setup/data').get_json()==values
 assert 'test-secret-123' not in str(c.get('/api/state').get_json())
 a.extensions['runtime'].store.engine.dispose()
 b=create_app(path)
 assert b.test_client().get('/api/activities/setup/data').get_json()==values
 token=bind(b.extensions['runtime'])
 try:assert Store.get('setup.completed',False) is True
 finally:unbind(token)
 assert b'test-secret-123' not in path.read_bytes()

def test_get_set_types_and_atomic_validation(tmp_path):
 repository=KeyValueRepository(tmp_path/'state.sqlite3')
 assert repository.get('missing',False) is False
 for key,value in {'flag':True,'count':0,'empty':'','none':None,'object':{'x':[1,2]}}.items():
  repository.set(key,value);assert repository.get(key)==value
 repository.set('flag',False);assert repository.get('flag') is False
 with pytest.raises(ValueError):repository.set_many({'valid':1,'':2})
 assert repository.get('valid') is None

def test_invalid_form_does_not_mark_completed(tmp_path):
 a=create_app(tmp_path/'state.sqlite3');c=a.test_client()
 c.post('/api/activities/setup/run',json={'database_name':'soil','username':'','password':'x'},headers=H)
 assert finish(c)['status']=='failed'
 assert a.extensions['runtime'].store.get('setup.completed',False) is False
 assert c.get('/api/activities/setup/data').get_json()=={}
