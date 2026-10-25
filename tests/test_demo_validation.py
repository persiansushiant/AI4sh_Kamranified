import contextlib,contextvars,os,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
import nbformat
from nbclient import NotebookClient
from app import create_app
from app.services.workspace_context import bind,unbind
from app.services.persistent_store import Store
from app.repositories.key_value_repository import KeyValueRepository

force_failure=False

def fake_execute(self,**kwargs):
    self.clear_before_next_output=False
    namespace={}
    context=contextvars.Context()
    previous=os.getcwd()
    import time
    sleep=time.sleep
    import app.services.workspace_context as wc
    fallback=wc.notebook_services
    try:
        os.chdir(kwargs['cwd'])
        time.sleep=lambda seconds:None
        for index,cell in enumerate(self.nb.cells):
            if cell.cell_type!='code':continue
            class Stream:
                def write(stream,text):
                    if text:self.process_message(dict(msg_type='stream',header={'msg_type':'stream'},content=dict(name='stdout',text=text),parent_header={}),cell,index)
                def flush(stream):pass
            try:
                code=cell.source.replace('SIMULATE_ERROR = False','SIMULATE_ERROR = True') if force_failure else cell.source
                with contextlib.redirect_stdout(Stream()):context.run(exec,compile(code,'<demo-cell>','exec'),namespace)
            except Exception as exc:
                self.process_message(dict(msg_type='error',header={'msg_type':'error'},content=dict(ename=type(exc).__name__,evalue=str(exc),traceback=[]),parent_header={}),cell,index)
            self.on_cell_executed(cell=cell,cell_index=index,execute_reply={})
    finally:
        time.sleep=sleep
        wc.notebook_services=fallback
        os.chdir(previous)
    return self.nb
NotebookClient.execute=fake_execute

with tempfile.TemporaryDirectory() as tmp:
    os.environ['HOME']=tmp
    app=create_app(Path(tmp)/'demo.sqlite3')
    runtime=app.extensions['runtime']
    client=app.test_client()
    assert client.get('/').status_code==200
    assert client.get('/api/activities/import_data/ui').status_code==200
    def data():return client.get('/api/activities/import_data/data').get_json()
    state=data()
    assert len(state['actions'])==3
    assert [a['id'] for a in state['actions'] if a['enabled']]==['prepare_demo']
    assert client.post('/api/activities/import_data/run',json={'action':'prepare_demo'}).status_code==403
    token=bind(runtime)
    try:
        activity=runtime.registry['import_data']
        try:activity.run({'action':'run_demo'})
        except ValueError:pass
        else:raise AssertionError('locked step ran')
        def execute(action,success):
            runtime.job={'id':action,'status':'running','activity':'import_data'}
            runtime._execute(activity,{'action':action})
            assert runtime.job['status']==('succeeded' if success else 'failed'),runtime.snapshot()
            assert not runtime.progress_state['active']
        execute('prepare_demo',True)
        assert data()['mode']==1
        assert Store.get('notebook_demo.actions')['prepare_demo']['status']=='succeeded'
        force_failure=True
        execute('run_demo',False)
        assert data()['mode']==1
        assert Store.get('notebook_demo.actions')['run_demo']['status']=='failed'
        assert 'log' in runtime.job['result']['message']
        force_failure=False
        execute('run_demo',True)
        assert data()['mode']==2
        restored=KeyValueRepository(Path(tmp)/'demo.sqlite3')
        assert restored.get('notebook_demo.mode')==2
        assert restored.get('notebook_demo.actions')['run_demo']['status']=='succeeded'
        assert Store.get('import_data.mode') is None
        execute('reset_demo',True)
        assert data()['mode']==0
        from app.services.import_data_controls import recover_interrupted_actions
        Store.set('notebook_demo.actions',{'run_demo':{'status':'running'}})
        recover_interrupted_actions()
        assert Store.get('notebook_demo.actions')['run_demo']['status']=='interrupted'
        assert any('Intentional demo error' in e['message'] for e in runtime.snapshot()['logs'])
    finally:
        unbind(token)
        runtime.close()
print('PASS: actual sample cell code with simulated kernel messages; Flask routes, locks, success/failure/retry/reset, progress cleanup, SQLite persistence and isolated keys')
