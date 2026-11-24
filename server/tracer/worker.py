"""Outbound-only 112 worker. Scoped credential never enters inference process."""
import fcntl,hashlib,json,os,signal,subprocess,sys,threading,time,shutil
from pathlib import Path
import httpx
from engine import probe
CONFIG=json.loads(Path(os.environ['WEB_TRACER_CONFIG']).read_text())
ROOT=Path(CONFIG['root']);ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
lock=(ROOT/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
class LeaseLost(Exception):pass

CONNECTIONS=threading.local()
def call(action,ident='',data=None):
    for attempt in range(3):
        client=getattr(CONNECTIONS,'client',None)
        if client is None:
            client=httpx.Client(timeout=20,follow_redirects=False,limits=httpx.Limits(keepalive_expiry=60))
            CONNECTIONS.client=client
        try:
            r=client.post(CONFIG['endpoint'],headers={'x-hc-worker':CONFIG['worker_key']},
              json={'environment':'production','action':action,'id':ident,'data':data or {}})
            if r.status_code in (409,410):raise LeaseLost()
            if r.status_code>=500:raise httpx.ConnectError('temporary_bridge_failure')
            if r.status_code!=200:raise RuntimeError('bridge_http_'+str(r.status_code))
            return r.json()
        except httpx.TransportError:
            client.close();CONNECTIONS.client=None
            if attempt==2:raise
            time.sleep(attempt+1)

def process(task):
    ident=task['id']
    if len(ident)!=48 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('invalid_job')
    folder=ROOT/ident;folder.mkdir(mode=0o700,exist_ok=True)
    (folder/'progress.json').unlink(missing_ok=True)
    lease={'lease':task['lease']};stop=threading.Event();lost=threading.Event();child=None
    stage={'stage':'downloading','progress':0}
    def heartbeat():
        while not stop.is_set():
            try:
                progress=stage.copy()
                if child is not None and (folder/'progress.json').exists():
                    progress=json.loads((folder/'progress.json').read_text())
                call('heartbeat',ident,{**lease,**progress})
            except Exception:
                lost.set();return
            stop.wait(15)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        if not (folder/'source').exists() or (folder/'source').stat().st_size!=task['size_bytes']:
            for attempt in range(5):
                try:
                    count=0;start=time.monotonic()
                    with httpx.stream('GET',task['source_url'],timeout=45,follow_redirects=False) as response:
                        response.raise_for_status()
                        with (folder/'source.part').open('wb') as out:
                            for chunk in response.iter_bytes(262144):
                                if lost.is_set() or time.monotonic()-start>600:raise LeaseLost()
                                count+=len(chunk)
                                if count>task['size_bytes'] or count>536870912:raise ValueError('source_size')
                                out.write(chunk)
                    if count!=task['size_bytes']:raise ValueError('source_size')
                    break
                except (httpx.TransportError,httpx.HTTPStatusError):
                    if lost.is_set():raise LeaseLost()
                    if attempt==4:raise
                    time.sleep(2**attempt)
            (folder/'source.part').replace(folder/'source')
        if task['operation']=='probe':
            stage.update(stage='probing');video=probe(folder/'source')
            call('finish',ident,{**lease,'state':'imported','video':video});return
        safe={k:v for k,v in task.items() if k not in ('source_url','lease')}
        (folder/'task.json').write_text(json.dumps(safe));(folder/'result.json').unlink(missing_ok=True)
        env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LD_LIBRARY_PATH','ACECUT_MODELS','ACECUT_FUSED','GOLFCUT_TRACKNET')}
        env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
        with (folder/'inference.log').open('w') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('engine.py')),str(folder),CONFIG['app']],
               stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            began=time.monotonic()
            while child.poll() is None:
                if lost.is_set():raise LeaseLost()
                if time.monotonic()-began>900:raise TimeoutError('inference_timeout')
                time.sleep(1)
            if child.returncode:raise RuntimeError('inference_failed')
        result=json.loads((folder/'result.json').read_text())
        if result['state']=='ready':
            stage.update(stage='returning',progress=95);child=None
            artifact=call('artifact',ident,lease)
            for attempt in range(5):
                try:
                    with (folder/'result.mp4').open('rb') as video:
                        with httpx.Client(timeout=120,follow_redirects=False) as client:
                            response=client.put(artifact['upload_url'],content=video.read(),headers={'Content-Type':'video/mp4'})
                    # A prior PUT can succeed while its response is lost. finish
                    # independently verifies the artifact's expected byte size.
                    if response.status_code == 409 or (response.status_code == 400 and 'Duplicate' in response.text):
                        break
                    response.raise_for_status()
                    break
                except (httpx.TransportError,httpx.HTTPStatusError):
                    if lost.is_set():raise LeaseLost()
                    if attempt == 4:raise
                    time.sleep(2**attempt)
            result['render']['path']=artifact['path']
        call('finish',ident,{**lease,**result})
    except LeaseLost:
        pass
    except Exception as error:
        print(json.dumps({'job':ident,'error':type(error).__name__}),flush=True)
        try:call('finish',ident,{**lease,'state':'failed','error_code':'processing_failed'})
        except Exception:pass
    finally:
        stop.set();thread.join(timeout=35)
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGKILL);child.wait()

last_cleanup=0
while True:
    try:
        if time.time()-last_cleanup>300:
            call('cleanup')
            for folder in ROOT.iterdir():
                if folder.is_dir() and time.time()-folder.stat().st_mtime>86400:shutil.rmtree(folder)
            last_cleanup=time.time()
        task=call('poll').get('task')
        if task:process(task)
        else:time.sleep(2)
    except Exception as error:
        print(json.dumps({'event':'retry','error':type(error).__name__,'connection_detail':str(error)[:160] if isinstance(error,httpx.ConnectError) else None}),flush=True);time.sleep(5)
