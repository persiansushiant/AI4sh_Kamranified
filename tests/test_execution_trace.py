import pytest
from app import create_app
from app.services.workspace_context import bind, unbind
from app.services.execution_trace import Trace
from app.services.activity_log import Log
from test_persistent_store import finish, H

def test_trace_sections_statuses_and_validation(tmp_path):
 a=create_app(tmp_path/'state.sqlite3');s=a.extensions['runtime'];t=bind(s)
 try:
  for section in ['job','scheme','pilot','process','dispatcher','sql','excel','ml']:
   Trace.success(section,'Completed')
  Trace.error('sql','Query failed');Trace.warning('excel','Missing cells');Trace.info('pilot','Started')
  Log.error('Compatibility error')
  with pytest.raises(ValueError):Trace.record('unknown','Test')
  with pytest.raises(ValueError):Trace.record('job','Test','unknown')
 finally:unbind(t)
 entries=s.snapshot()['logs']
 assert {e['section'] for e in entries}=={'job','scheme','pilot','process','dispatcher','sql','excel','ml'}
 assert entries[-1]['status']=='error'
 assert entries[-1]['section']=='process'
 assert len({e['id'] for e in entries})==len(entries)

def test_trace_filters_and_error_classification(tmp_path):
 a=create_app(tmp_path/'state.sqlite3');c=a.test_client()
 choices=c.get('/api/activities/log/data').get_json()
 assert len(choices['sections'])==8
 assert choices['statuses']==['info','success','warning','error']
 html=c.get('/api/activities/log/ui').get_data(as_text=True)
 assert 'traceSection' in html and 'traceStatus' in html
 c.post('/api/activities/setup/run',json={},headers=H)
 assert finish(c)['status']=='failed'
 entries=c.get('/api/state').get_json()['logs']
 assert any(e['section']=='job' and e['status']=='error' for e in entries)

def test_bounded_trace_buffer(tmp_path):
 s=create_app(tmp_path/'state.sqlite3').extensions['runtime']
 for i in range(405):s.log(str(i),'dispatcher','info')
 logs=s.snapshot()['logs']
 assert len(logs)==400 and logs[0]['message']=='5'
