"""Bounded signed GET streaming inside an explicitly selected replica namespace.

No host port, bridge endpoint, redirects, retries or credential argv. This
transport does not create a replica or prove maintained host isolation.
"""
import re,subprocess,threading,urllib.error,time
from formal_s3_export import ReadOnlyS3
from formal_snapshot_linux import FormalSnapshotError,require,current_owner_guard,observation_timeout

def _end_unmanaged_client(process,primary):
    """Constructor failure: no response owns this exact client yet."""
    uncertain=False
    try:
        if process.poll() is None:process.kill()
        process.wait(timeout=5)
    except (OSError,subprocess.TimeoutExpired):uncertain=True
    if process.poll() is not None:
        for stream in (process.stdin,process.stdout):
            try:
                if stream is not None and not stream.closed:stream.close()
            except OSError:uncertain=True
    if uncertain:primary.clientCleanupUncertain=True

class _ExecResponse:
    def __init__(self,process,timeout,guard):
        self.process=process;self.closed=False;self.finished=False;self.count=0;self.timed_out=False
        self.guard=guard;self.deadline=time.monotonic()+observation_timeout(timeout+5)
        def expire():
            self.timed_out=True
            try:
                if process.poll() is None:process.kill()
            except OSError:self.client_cleanup_uncertain=True
        self.timer=threading.Timer(timeout+5,expire);self.timer.daemon=True;self.timer.start()
    def _current(self):
        current_owner_guard(self.guard,code='FORMAL_EXEC_OWNER_GUARD_REQUIRED')
        require(time.monotonic()<self.deadline and not self.timed_out,'FORMAL_EXEC_STREAM_TIMEOUT')
    def _end_client(self,*,worker=None,primary=None):
        self.timer.cancel();uncertain=False
        try:
            if self.process.poll() is None:self.process.kill()
            self.process.wait(timeout=5)
        except (OSError,subprocess.TimeoutExpired):uncertain=True
        if worker is not None:
            worker.join(timeout=5)
            uncertain=uncertain or worker.is_alive()
        if (worker is None or not worker.is_alive()) and self.process.poll() is not None:
            for stream in (self.process.stdin,self.process.stdout):
                try:
                    if stream is not None and not stream.closed:stream.close()
                except OSError:uncertain=True
        self.closed=True
        if uncertain:
            if primary is not None:primary.clientCleanupUncertain=True
            else:raise FormalSnapshotError('FORMAL_EXEC_CLOSE_UNCERTAIN')
    def _guarded_io(self,function):
        # Pure I/O on a worker; the claim/deadline guard stays on its owner.
        worker=None;done=threading.Event();value=[];errors=[]
        try:
            self._current()
            def run():
                try:value.append(function())
                except BaseException as error:errors.append(error)
                finally:done.set()
            worker=threading.Thread(target=run,daemon=True);worker.start()
            while not done.wait(0.05):self._current()
            self._current();worker.join(timeout=5)
            require(not worker.is_alive(),'FORMAL_EXEC_IO_UNCERTAIN')
            if errors:raise errors[0]
            require(len(value)==1,'FORMAL_EXEC_IO_UNCERTAIN')
            return value[0]
        except BaseException as error:
            self._end_client(worker=worker,primary=error)
            raise
    def parse_headers(self):
        first=self._guarded_io(lambda:self.process.stdout.readline(8193))
        require(re.fullmatch(rb'HTTP/1\.[01] [0-9]{3}[^\r\n]*\r\n',first) is not None,
                'FORMAL_EXEC_HTTP_INVALID')
        self.status=int(first.split()[1]);headers={};size=len(first)
        while True:
            line=self._guarded_io(lambda:self.process.stdout.readline(8193));size+=len(line)
            require(line and len(line)<=8192 and size<=65536 and line.endswith(b'\r\n'),'FORMAL_EXEC_HTTP_INVALID')
            if line==b'\r\n':break
            key,separator,value=line[:-2].partition(b':')
            require(separator and re.fullmatch(rb'[A-Za-z0-9-]+',key),'FORMAL_EXEC_HTTP_INVALID')
            name=key.decode('ascii').lower()
            try:text=value.strip().decode('latin-1')
            except UnicodeError:raise FormalSnapshotError('FORMAL_EXEC_HTTP_INVALID') from None
            require(not any(ord(c)<32 or ord(c)==127 for c in text),'FORMAL_EXEC_HTTP_INVALID')
            require(name not in headers or name=='vary','FORMAL_EXEC_HTTP_DUPLICATE_HEADER_'+name.upper().replace('-','_'))
            # Vary is a list-valued HTTP field. Combine its repeated lines;
            # content length, identity and metadata duplicates still refuse.
            headers[name]=headers[name]+', '+text if name in headers else text
        require('transfer-encoding' not in headers and
            re.fullmatch('[0-9]+',headers.get('content-length','')),'FORMAL_EXEC_HTTP_LENGTH_REQUIRED')
        self.headers=headers;self.length=int(headers['content-length'])
        return self
    def read(self,size):
        require(type(size) is int and 0<size<=1024*1024+1 and not self.closed,'FORMAL_EXEC_READ_INVALID')
        try:raw=self._guarded_io(lambda:self.process.stdout.read(size))
        except OSError:raise FormalSnapshotError('FORMAL_EXEC_STREAM_FAILED') from None
        self.count+=len(raw)
        require(self.count<=self.length,'FORMAL_EXEC_CONTENT_LENGTH_CHANGED')
        if not self.finished and (not raw or self.count==self.length):
            if self.count==self.length:
                require(self._guarded_io(lambda:self.process.stdout.read(1))==b'','FORMAL_EXEC_CONTENT_LENGTH_CHANGED')
            try:code=self._guarded_io(lambda:self.process.wait(timeout=5))
            except subprocess.TimeoutExpired:raise FormalSnapshotError('FORMAL_EXEC_STREAM_TIMEOUT') from None
            require(not self.timed_out and code==0,'FORMAL_EXEC_TRANSFER_FAILED')
            require(self.count==self.length,'FORMAL_EXEC_CONTENT_TRUNCATED')
            self.finished=True;self.timer.cancel()
        return raw
    def close(self):
        if self.closed:return
        self._end_client()
    def __enter__(self):return self
    def __exit__(self,*args):
        if not self.closed:self._end_client(primary=args[1])

class ContainerReadOnlyS3(ReadOnlyS3):
    def __init__(self,container_id,access,secret,*,guard,timeout=30):
        current_owner_guard(guard,code='FORMAL_EXEC_OWNER_GUARD_REQUIRED')
        require(type(container_id) is str and re.fullmatch('[0-9a-f]{64}',container_id),'FORMAL_EXEC_CONTAINER_INVALID')
        self.container_id=container_id;self.guard=guard
        super().__init__('http://127.0.0.1:9000',access,secret,timeout=timeout)
    def _open(self,request):
        current_owner_guard(self.guard,code='FORMAL_EXEC_OWNER_GUARD_REQUIRED')
        require(request.get_method()=='GET' and request.full_url.startswith(self.endpoint+'/'),
                'FORMAL_EXEC_GET_SCOPE_INVALID')
        def quote(value):
            require(type(value) is str and not any(c in value for c in '\r\n\0'),'FORMAL_EXEC_CONFIG_INVALID')
            return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'
        lines=['url = '+quote(request.full_url),'request = "GET"','dump-header = "-"',
            'output = "-"','silent','show-error','noproxy = "*"','proxy = ""',
            'proto = "=http"','max-time = '+str(self.timeout),'connect-timeout = '+str(self.timeout)]
        lines.extend('header = '+quote(key+': '+value) for key,value in request.header_items())
        config=('\n'.join(lines)+'\n').encode('utf-8')
        require(len(config)<=16384,'FORMAL_EXEC_CONFIG_TOO_LARGE')
        process=None;response=None
        try:
            process=subprocess.Popen(['docker','exec','-i',self.container_id,'curl','--disable','--config','-'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            response=_ExecResponse(process,self.timeout,self.guard)
            written=response._guarded_io(lambda:process.stdin.write(config))
            require(written==len(config),'FORMAL_EXEC_CONFIG_WRITE_INCOMPLETE')
            response._guarded_io(process.stdin.close);response.parse_headers()
            if response.status!=200:
                raise urllib.error.HTTPError(request.full_url,response.status,'REPLICA_HTTP_ERROR',response.headers,response)
            return response
        except urllib.error.HTTPError:raise
        except BaseException as error:
            if response is not None:
                if not response.closed:response._end_client(primary=error)
            elif process is not None:_end_unmanaged_client(process,error)
            if isinstance(error,(OSError,ValueError)):
                failure=FormalSnapshotError('FORMAL_EXEC_TRANSPORT_FAILED')
                if getattr(error,'clientCleanupUncertain',False):failure.clientCleanupUncertain=True
                raise failure from None
            raise
