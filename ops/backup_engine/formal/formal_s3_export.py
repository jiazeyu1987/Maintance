"""Finite isolated S3 full-version export, not final recovery/consistency proof."""
import datetime,hashlib,hmac,http.client,json,os,re,time
from pathlib import Path
import urllib.parse,urllib.request,urllib.error
import xml.etree.ElementTree as ET
from formal_snapshot_linux import FormalSnapshotError,require,safe_file,_existing_file,_hash_object,_canonical_bytes,current_owner_guard

def _strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'FORMAL_S3_JSON_DUPLICATE_KEY');result[key]=value
        return result
    def constant(value):raise FormalSnapshotError('FORMAL_S3_JSON_NONFINITE')
    try:return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,ValueError):raise FormalSnapshotError('FORMAL_S3_JSON_INVALID') from None

def _restore_metadata(headers):
    protected={'x-amz-object-lock-mode','x-amz-object-lock-retain-until-date','x-amz-object-lock-legal-hold'}
    require(type(headers) is dict and all(type(k) is str and type(v) is str and
        not any(c in k+v for c in '\r\n\0') and (k.startswith('x-amz-meta-') or k in protected or
        k in ('content-type','content-encoding','content-disposition','cache-control','expires'))
        for k,v in headers.items()),'FORMAL_S3_RESTORE_PROTECTION_UNSUPPORTED')
    mode=headers.get('x-amz-object-lock-mode');until=headers.get('x-amz-object-lock-retain-until-date')
    require((mode is None and until is None) or (mode in ('COMPLIANCE','GOVERNANCE') and type(until) is str and
        re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z',until)),
        'FORMAL_S3_RESTORE_PROTECTION_INVALID')
    if until is not None:
        try:datetime.datetime.fromisoformat(until.replace('Z','+00:00'))
        except ValueError:raise FormalSnapshotError('FORMAL_S3_RESTORE_PROTECTION_INVALID') from None
    require('x-amz-object-lock-legal-hold' not in headers or headers['x-amz-object-lock-legal-hold'] in ('ON','OFF'),
        'FORMAL_S3_RESTORE_PROTECTION_INVALID')
    return bool(protected.intersection(headers))

class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,message,headers,new_url):
        raise urllib.error.HTTPError(request.full_url,code,'REDIRECT_REFUSED',headers,fp)

def _open_signed(request,timeout):
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),_RejectRedirect()).open(request,timeout=timeout)

class ReadOnlyS3:
    """Signed GET only; credentials stay in memory, errors expose fixed codes."""
    def __init__(self,endpoint,access,secret,*,timeout=30):
        parts=urllib.parse.urlsplit(endpoint)
        require(parts.scheme in ('http','https') and parts.hostname and not parts.username and
                not parts.password and parts.path in ('','/') and not parts.query and not parts.fragment,
                'FORMAL_S3_ENDPOINT_INVALID')
        require(all(type(x) is str and x and not any(c in x for c in '\r\n\0') for x in (access,secret)),
                'FORMAL_S3_CREDENTIAL_INVALID')
        require(type(timeout) is int and 0<timeout<=60,'FORMAL_S3_TIMEOUT_INVALID')
        self.endpoint=endpoint.rstrip('/');self.host=parts.netloc;self._access=access;self._secret=secret;self.timeout=timeout
    def _open(self,request):
        return _open_signed(request,timeout=self.timeout)
    def _get(self,bucket,key='',params=(),*,expected_absence=None):
        quote=lambda x:urllib.parse.quote(x,safe='-_.~')
        path='/'+quote(bucket)+('/'+urllib.parse.quote(key,safe='/-_.~') if key else '')
        query='&'.join(k+'='+v for k,v in sorted((quote(k),quote(v)) for k,v in params))
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');date=stamp[:8]
        empty=hashlib.sha256(b'').hexdigest();signed='host;x-amz-content-sha256;x-amz-date'
        headers='host:'+self.host+'\nx-amz-content-sha256:'+empty+'\nx-amz-date:'+stamp+'\n'
        canonical='GET\n'+path+'\n'+query+'\n'+headers+'\n'+signed+'\n'+empty
        scope=date+'/us-east-1/s3/aws4_request'
        string='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
        sign=lambda k,v:hmac.new(k,v.encode(),hashlib.sha256).digest()
        signing=sign(sign(sign(sign(('AWS4'+self._secret).encode(),date),'us-east-1'),'s3'),'aws4_request')
        auth='AWS4-HMAC-SHA256 Credential='+self._access+'/'+scope+', SignedHeaders='+signed+', Signature='+hmac.new(signing,string.encode(),hashlib.sha256).hexdigest()
        request=urllib.request.Request(self.endpoint+path+('?' +query if query else ''),method='GET',
            headers={'Host':self.host,'x-amz-date':stamp,'x-amz-content-sha256':empty,'Authorization':auth})
        try:return self._open(request)
        except urllib.error.HTTPError as error:
            if error.code==404 and expected_absence is not None:
                try:
                    raw=error.read(16385)
                    require(len(raw)<=16384,'FORMAL_S3_CONFIG_TOO_LARGE')
                    try:root=ET.fromstring(raw)
                    except ET.ParseError:raise FormalSnapshotError('FORMAL_S3_CONFIG_INVALID') from None
                    require(root.tag=='Error' and [n.text for n in root if n.tag=='Code']==[expected_absence],
                            'FORMAL_S3_CONFIG_ABSENCE_UNPROVEN')
                    return {'httpStatus':404,'errorCode':expected_absence,
                            'rawSha256':hashlib.sha256(raw).hexdigest(),'rawBytes':len(raw)}
                finally:error.close()
            code=error.code;error.close()
            raise FormalSnapshotError('FORMAL_S3_HTTP_'+str(code)) from None
        except (OSError,ValueError):raise FormalSnapshotError('FORMAL_S3_READ_FAILED') from None
    def versions(self,bucket,cursor):
        params=[('versions',''),('encoding-type','url'),('max-keys','1000')]
        if cursor:params += [('key-marker',cursor[0]),('version-id-marker',cursor[1])]
        with self._get(bucket,params=params) as response:raw=response.read(1024*1024+1)
        require(len(raw)<=1024*1024,'FORMAL_S3_PAGE_TOO_LARGE')
        def tag(node,name):
            values=[n.text or '' for n in node if n.tag.split('}')[-1]==name]
            require(len(values)==1,'FORMAL_S3_LIST_INVALID');return values[0]
        try:
            root=ET.fromstring(raw);rows=[]
            for node in root:
                kind=node.tag.split('}')[-1]
                if kind not in ('Version','DeleteMarker'):continue
                latest=tag(node,'IsLatest');require(latest in ('true','false'),'FORMAL_S3_LIST_INVALID')
                row={'kind':'version' if kind=='Version' else 'delete-marker','key':urllib.parse.unquote_plus(tag(node,'Key')),
                     'versionId':tag(node,'VersionId'),'isLatest':latest=='true','lastModified':tag(node,'LastModified')}
                if kind=='Version':row.update(size=int(tag(node,'Size')),etag=tag(node,'ETag'))
                rows.append(row)
            truncated=tag(root,'IsTruncated');require(truncated in ('true','false'),'FORMAL_S3_LIST_INVALID')
            next_cursor=(urllib.parse.unquote_plus(tag(root,'NextKeyMarker')),tag(root,'NextVersionIdMarker')) if truncated=='true' else None
            return rows,next_cursor
        except (ET.ParseError,ValueError):raise FormalSnapshotError('FORMAL_S3_LIST_INVALID') from None
    def content(self,bucket,key,version):
        response=self._get(bucket,key,[('versionId',version)])
        return response,{k.lower():v for k,v in response.headers.items()}
    def multipart_empty(self,bucket):
        """One successful whole-bucket query, never a sustained drain proof.

        Limit one is sufficient only when the complete first page is empty.
        Any upload, truncation or filtering refuses; no abort/completion calls.
        """
        require(type(bucket) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket),
                'FORMAL_S3_CONFIG_SCOPE_INVALID')
        with self._get(bucket,params=[('uploads',''),('max-uploads','1')]) as response:
            require(response.status==200,'FORMAL_S3_MULTIPART_LIST_INVALID')
            raw=response.read(1024*1024+1)
        require(0<len(raw)<=1024*1024 and b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw,
                'FORMAL_S3_MULTIPART_LIST_INVALID')
        try:root=ET.fromstring(raw)
        except ET.ParseError:raise FormalSnapshotError('FORMAL_S3_MULTIPART_LIST_INVALID') from None
        namespace='{http://s3.amazonaws.com/doc/2006-03-01/}' if root.tag.startswith('{') else ''
        require(root.tag==namespace+'ListMultipartUploadsResult' and not root.attrib,
                'FORMAL_S3_MULTIPART_LIST_INVALID')
        fields={};uploads=0
        allowed={'Bucket','KeyMarker','UploadIdMarker','NextKeyMarker','NextUploadIdMarker',
                 'Prefix','Delimiter','EncodingType','MaxUploads','IsTruncated','Upload'}
        for node in root:
            name=node.tag[len(namespace):] if namespace else node.tag
            require(node.tag==namespace+name and name in allowed,'FORMAL_S3_MULTIPART_LIST_INVALID')
            if name=='Upload':uploads+=1;continue
            require(name not in fields and not list(node) and not node.attrib,
                    'FORMAL_S3_MULTIPART_LIST_INVALID')
            fields[name]=node.text or ''
        require(fields.get('Bucket')==bucket and fields.get('MaxUploads')=='1' and
                fields.get('IsTruncated') in ('true','false') and
                all(not fields.get(name,'') for name in ('Prefix','Delimiter','KeyMarker','UploadIdMarker')),
                'FORMAL_S3_MULTIPART_LIST_INVALID')
        require(uploads==0,'FORMAL_S3_MULTIPART_UPLOAD_PENDING')
        require(fields['IsTruncated']=='false' and
                all(not fields.get(name,'') for name in ('NextKeyMarker','NextUploadIdMarker')) and
                fields.get('EncodingType','') in ('','url'),'FORMAL_S3_MULTIPART_LIST_INVALID')
        return {'bucket':bucket,'state':'NO_MULTIPART_UPLOAD_OBSERVED','httpStatus':200,
                'rawSha256':hashlib.sha256(raw).hexdigest(),'rawBytes':len(raw),'maxUploads':1,
                'uploadCount':0,'isTruncated':False,'scope':'WHOLE_BUCKET_FROM_START'}
    def absent_configuration(self,bucket,configuration,error_code):
        codes={'lifecycle':'NoSuchLifecycleConfiguration','replication':'ReplicationConfigurationNotFoundError',
               'encryption':'ServerSideEncryptionConfigurationNotFoundError'}
        require(configuration in codes and error_code==codes[configuration] and type(bucket) is str and
                re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket),'FORMAL_S3_CONFIG_SCOPE_INVALID')
        result=self._get(bucket,params=[(configuration,'')],expected_absence=error_code)
        if type(result) is not dict:
            result.close()
            raise FormalSnapshotError('FORMAL_S3_REPLICA_EXTERNAL_DEPENDENCY_PRESENT')
        return dict(result,bucket=bucket,configuration=configuration)
    def replica_configuration(self,bucket,configuration):
        require(configuration in ('notification','versioning','object-lock') and type(bucket) is str and
            re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket),'FORMAL_S3_CONFIG_SCOPE_INVALID')
        response=self._get(bucket,params=[(configuration,'')],expected_absence=
            'ObjectLockConfigurationNotFoundError' if configuration=='object-lock' else None)
        if type(response) is dict:
            return dict(response,bucket=bucket,configuration=configuration,enabled=False)
        with response:raw=response.read(16385)
        require(len(raw)<=16384 and b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw,'FORMAL_S3_CONFIG_INVALID')
        try:root=ET.fromstring(raw)
        except ET.ParseError:raise FormalSnapshotError('FORMAL_S3_CONFIG_INVALID') from None
        name=lambda node:node.tag.split('}')[-1]
        required={'notification':'NotificationConfiguration','versioning':'VersioningConfiguration','object-lock':'ObjectLockConfiguration'}
        require(name(root)==required[configuration],'FORMAL_S3_CONFIG_INVALID')
        result={'bucket':bucket,'configuration':configuration,'httpStatus':200,
                'rawSha256':hashlib.sha256(raw).hexdigest(),'rawBytes':len(raw)}
        if configuration=='notification':
            require(not list(root) and not (root.text or '').strip(),'FORMAL_REPLICA_NOTIFICATION_PRESENT')
            return dict(result,externalNotificationEntries=0)
        if configuration=='versioning':
            states=[n.text for n in root if name(n)=='Status']
            require(len(states)<=1 and all(s in ('Enabled','Suspended') for s in states) and
                all(name(n) in ('Status','MfaDelete') for n in root),'FORMAL_S3_CONFIG_INVALID')
            return dict(result,status=states[0] if states else 'UNVERSIONED')
        enabled=[n.text for n in root if name(n)=='ObjectLockEnabled']
        require(enabled==['Enabled'] and all(name(n) in ('ObjectLockEnabled','Rule') for n in root),
                'FORMAL_S3_CONFIG_INVALID')
        # Preserve raw config digest. Default retention and individual object
        # retainUntil/hold still require actual restore equivalence separately.
        return dict(result,enabled=True)

def observe_replica_bucket_dependencies(client,buckets):
    """Actual GET observations; caller must bind them under maintained barriers.

    This does not authorize starting copied storage. Pending jobs/tier/global
    config, raw bucket metadata, notification and protection proof remain.
    """
    require(type(buckets) is list and buckets and len(buckets)<=1000 and
            all(type(b) is str for b in buckets) and len(set(buckets))==len(buckets),
            'FORMAL_S3_CONFIG_SCOPE_INVALID')
    observations=[]
    for bucket in buckets:
        for configuration,code in (('lifecycle','NoSuchLifecycleConfiguration'),
          ('replication','ReplicationConfigurationNotFoundError'),
          ('encryption','ServerSideEncryptionConfigurationNotFoundError')):
            observations.append(client.absent_configuration(bucket,configuration,code))
    return {'state':'BUCKET_DEPENDENCIES_OBSERVED_PENDING_FROZEN_BINDING','buckets':buckets,
            'observations':observations,'replicaStartupApproved':False}

class IsolatedRestoreS3(ReadOnlyS3):
    """Explicit approved isolated endpoint, no redirects/retry/bucket creation.

    Caller must bind this endpoint to the registered isolated target and provide
    its independently verified credentials. Equality is not deployment approval.
    """
    def __init__(self,endpoint,access,secret,*,approved_endpoint,timeout=30,verify_payload=True):
        self.verify_payload=verify_payload
        require(type(approved_endpoint) is str and endpoint==approved_endpoint,'FORMAL_S3_WRITE_ENDPOINT_UNAPPROVED')
        super().__init__(endpoint,access,secret,timeout=timeout)
    def empty_versioned(self,bucket):
        with self._get(bucket,params=[('versioning','')]) as response:raw=response.read(16385)
        require(len(raw)<=16384,'FORMAL_S3_CONFIG_TOO_LARGE')
        try:
            root=ET.fromstring(raw)
            states=[node.text for node in root if node.tag.split('}')[-1]=='Status']
            require(states==['Enabled'],'FORMAL_S3_RESTORE_VERSIONING_REQUIRED')
        except ET.ParseError:raise FormalSnapshotError('FORMAL_S3_CONFIG_INVALID') from None
        _require_empty_multipart_observation(self.multipart_empty(bucket),bucket)
        rows,cursor=self.versions(bucket,None)
        return rows==[] and cursor is None
    def _write(self,method,bucket,key,*,path=None,headers=None,size=0,sha=None):
        require(method in ('PUT','DELETE') and type(bucket) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',bucket) and
                type(key) is str and key and '\0' not in key,'FORMAL_S3_WRITE_INPUT_INVALID')
        metadata=dict(headers or {})
        if self.verify_payload and _restore_metadata(metadata):
            require(self.replica_configuration(bucket,'object-lock').get('enabled') is True,
                'FORMAL_S3_RESTORE_OBJECT_LOCK_REQUIRED')
        require(type(size) is int and size>=0,'FORMAL_S3_WRITE_INPUT_INVALID')
        if method=='PUT':
            path=Path(path)
            if self.verify_payload:
                actual,actual_size=_hash_object(path)
                require(actual=='sha256:'+str(sha) and actual_size==size,'FORMAL_S3_RESTORE_CONTENT_CHANGED')
            else:
                size=path.stat().st_size
                sha='UNSIGNED-PAYLOAD'
        else:sha=hashlib.sha256(b'').hexdigest()
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');date=stamp[:8]
        request_path='/'+urllib.parse.quote(bucket,safe='-_.~')+'/'+urllib.parse.quote(key,safe='/-_.~')
        values=dict(metadata,host=self.host,**{'x-amz-content-sha256':sha,'x-amz-date':stamp})
        signed=';'.join(sorted(values))
        canonical_headers=''.join(k+':'+ ' '.join(values[k].split())+'\n' for k in sorted(values))
        canonical=method+'\n'+request_path+'\n\n'+canonical_headers+'\n'+signed+'\n'+sha
        scope=date+'/us-east-1/s3/aws4_request'
        string='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
        sign=lambda k,v:hmac.new(k,v.encode(),hashlib.sha256).digest()
        signing=sign(sign(sign(sign(('AWS4'+self._secret).encode(),date),'us-east-1'),'s3'),'aws4_request')
        values['authorization']='AWS4-HMAC-SHA256 Credential='+self._access+'/'+scope+', SignedHeaders='+signed+', Signature='+hmac.new(signing,string.encode(),hashlib.sha256).hexdigest()
        values['content-length']=str(size)
        parts=urllib.parse.urlsplit(self.endpoint)
        connection=(http.client.HTTPSConnection if parts.scheme=='https' else http.client.HTTPConnection)(parts.hostname,parts.port,timeout=self.timeout)
        deadline=time.monotonic()+self.timeout
        try:
            connection.putrequest(method,request_path,skip_host=True,skip_accept_encoding=True)
            for k,v in values.items():connection.putheader(k,v)
            connection.endheaders()
            if method=='PUT':
                digest=hashlib.sha256();count=0
                with path.open('rb') as source:
                    while True:
                        require(time.monotonic()<deadline,'FORMAL_S3_WRITE_TIMEOUT')
                        chunk=source.read(1024*1024)
                        if not chunk:break
                        count+=len(chunk)
                        connection.send(chunk)
                        if self.verify_payload:
                            require(count<=size,'FORMAL_S3_RESTORE_CONTENT_CHANGED')
                            digest.update(chunk)
                if self.verify_payload:
                    require(count==size and digest.hexdigest()==sha,'FORMAL_S3_RESTORE_CONTENT_CHANGED')
            response=connection.getresponse()
            require(response.status==(200 if method=='PUT' else 204),'FORMAL_S3_WRITE_HTTP_'+str(response.status))
            result={k.lower():v for k,v in response.getheaders()}
            require(response.read(16385)==b'','FORMAL_S3_WRITE_RESPONSE_INVALID')
            version=result.get('x-amz-version-id')
            require(type(version) is str and version and version!='null' and '\0' not in version,'FORMAL_S3_RESTORE_VERSION_INVALID')
            if method=='DELETE':require(result.get('x-amz-delete-marker')=='true','FORMAL_S3_DELETE_MARKER_INVALID')
            return version
        except (OSError,ValueError,http.client.HTTPException):raise FormalSnapshotError('FORMAL_S3_WRITE_FAILED') from None
        finally:connection.close()
    def put_version(self,bucket,key,path,headers,size,sha):
        return self._write('PUT',bucket,key,path=path,headers=headers,size=size,sha=sha)
    def delete_marker(self,bucket,key):return self._write('DELETE',bucket,key)

def _require_empty_multipart_observation(value,bucket):
    require(type(value) is dict and set(value)=={'bucket','state','httpStatus','rawSha256','rawBytes',
            'maxUploads','uploadCount','isTruncated','scope'} and value['bucket']==bucket and
            value['state']=='NO_MULTIPART_UPLOAD_OBSERVED' and value['scope']=='WHOLE_BUCKET_FROM_START' and
            type(value['httpStatus']) is int and value['httpStatus']==200 and
            type(value['rawBytes']) is int and 0<value['rawBytes']<=1024*1024 and
            type(value['rawSha256']) is str and re.fullmatch('[0-9a-f]{64}',value['rawSha256']) and
            type(value['maxUploads']) is int and value['maxUploads']==1 and
            type(value['uploadCount']) is int and value['uploadCount']==0 and value['isTruncated'] is False,
            'FORMAL_S3_MULTIPART_LIST_INVALID')


def export_s3_versions(client,buckets,destination,*,guard,timeout=7200):
    """Stream all exact versions and tombstones; retain failed private bytes.

    Requires isolated immutable replica/verified internal dependency preconditions.
    Output remains pending restore, preserves version IDs only as source mapping.
    """
    current_owner_guard(guard,code='FORMAL_S3_EXPORT_OWNER_GUARD_REQUIRED')
    require(type(buckets) is list and buckets and len(buckets)==len(set(buckets)) and
        all(type(b) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',b) for b in buckets),
        'FORMAL_S3_BUCKETS_INVALID')
    require(type(timeout) is int and 0<timeout<=7200,'FORMAL_S3_TIMEOUT_INVALID')
    target=safe_file(destination);target.mkdir(mode=0o700);started=time.monotonic()
    def budget():
        require(time.monotonic()-started<timeout,'FORMAL_S3_EXPORT_TIMEOUT')
        current_owner_guard(guard,code='FORMAL_S3_EXPORT_OWNER_GUARD_REQUIRED')
    def listing(bucket):
        cursor=None;cursors=set();seen=set();rows=[]
        while True:
            budget();page,next_cursor=client.versions(bucket,cursor);budget()
            require(type(page) is list,'FORMAL_S3_LIST_INVALID')
            for row in page:
                require(type(row) is dict and row.get('kind') in ('version','delete-marker') and
                    all(type(row.get(k)) is str and row[k] and '\0' not in row[k] for k in ('key','versionId')) and
                    type(row.get('isLatest')) is bool,'FORMAL_S3_LIST_INVALID')
                identity=(row['key'],row['versionId']);require(identity not in seen,'FORMAL_S3_VERSION_DUPLICATE')
                seen.add(identity);rows.append(row);require(len(rows)<=500000,'FORMAL_S3_LIST_TOO_LARGE')
            if next_cursor is None:break
            require(type(next_cursor) is tuple and len(next_cursor)==2 and next_cursor not in cursors,
                    'FORMAL_S3_CURSOR_INVALID')
            cursors.add(next_cursor);cursor=next_cursor
        return rows
    def write(path,raw,*,failure=False):
        if not failure:budget()
        with path.open('xb') as f:os.chmod(path,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
    try:
        observe=getattr(client,'multipart_empty',None)
        require(callable(observe),'FORMAL_S3_MULTIPART_OBSERVATION_REQUIRED')
        def empty_observations():
            records=[]
            for bucket in buckets:
                budget();value=observe(bucket);budget()
                _require_empty_multipart_observation(value,bucket);records.append(dict(value))
            return records
        before=empty_observations()
        inventory=target/'versions.jsonl';pending=target/'current-object.pending'
        counts={'versionCount':0,'deleteMarkerCount':0,'uniqueContentCount':0,'totalVersionBytes':0};content_seen=set()
        with inventory.open('xb') as output:
            os.chmod(inventory,0o600)
            for bucket in buckets:
                initial=listing(bucket)
                for row in initial:
                    budget();record=dict(row,bucket=bucket)
                    if row['kind']=='delete-marker':counts['deleteMarkerCount']+=1
                    else:
                        require(type(row.get('size')) is int and row['size']>=0 and type(row.get('etag')) is str,
                                'FORMAL_S3_LIST_INVALID')
                        response,headers=client.content(bucket,row['key'],row['versionId'])
                        try:
                            budget()
                            require(headers.get('x-amz-version-id')==row['versionId'] or
                                (row['versionId']=='null' and headers.get('x-amz-version-id') is None),
                                'FORMAL_S3_VERSION_MISMATCH')
                            require(headers.get('etag')==row['etag'] and headers.get('content-length')==str(row['size']),
                                    'FORMAL_S3_METADATA_CHANGED')
                            digest=hashlib.sha256();size=0
                            with pending.open('xb') as f:
                                os.chmod(pending,0o600)
                                while True:
                                    budget();chunk=response.read(1024*1024);budget()
                                    if not chunk:break
                                    size+=len(chunk);require(size<=row['size'],'FORMAL_S3_CONTENT_SIZE_MISMATCH')
                                    f.write(chunk);digest.update(chunk)
                                f.flush();os.fsync(f.fileno())
                        finally:response.close()
                        require(size==row['size'],'FORMAL_S3_CONTENT_SIZE_MISMATCH');sha=digest.hexdigest()
                        relative='objects/sha256/'+sha[:2]+'/'+sha+'.bin';content=target/relative
                        if sha in content_seen:
                            actual,actual_size=_hash_object(content,guard=budget)
                            require(actual=='sha256:'+sha and actual_size==size,'FORMAL_S3_REUSED_CONTENT_CHANGED')
                        else:
                            budget();content.parent.mkdir(mode=0o700,parents=True,exist_ok=True);os.link(pending,content)
                            content_seen.add(sha);counts['uniqueContentCount']+=1
                        pending.unlink()
                        record.update(sha256=sha,repositoryPath=relative,headers={k:v for k,v in headers.items()
                            if k.startswith(('x-amz-meta-','x-amz-object-lock-','x-amz-server-side-encryption','x-amz-storage-class')) or
                            k in ('content-type','content-encoding','content-disposition','cache-control','expires')})
                        counts['versionCount']+=1;counts['totalVersionBytes']+=size
                    budget();output.write(_canonical_bytes(record))
                require(listing(bucket)==initial,'FORMAL_S3_LIST_CHANGED')
            output.flush();os.fsync(output.fileno())
        actual,size=_hash_object(inventory,guard=budget)
        after=empty_observations()
        multipart=_canonical_bytes({'state':'MULTIPART_EMPTY_POINT_OBSERVATIONS','before':before,'after':after})
        write(target/'multipart-observations.json',multipart)
        result=dict(counts,buckets=buckets,state='S3_EXPORTED_PENDING_RESTORE_PROOF',inventorySha256=actual[7:],inventoryBytes=size,
                    multipartObservationsSha256=hashlib.sha256(multipart).hexdigest())
        write(target/'export-receipt.json',_canonical_bytes(result));budget();return result
    except Exception as error:
        code=error.code if isinstance(error,FormalSnapshotError) else 'FORMAL_S3_EXPORT_FAILED'
        write(target/'failed.json',_canonical_bytes({'state':'FAILED_RETAINED','code':code}),failure=True)
        raise FormalSnapshotError(code) from None

def validate_bucket_mapping(bucket_mapping,buckets):
    """Complete one-to-one explicit mapping; never infer an identity target."""
    require(type(bucket_mapping) is dict and type(buckets) is list and buckets and
            len(buckets)==len(set(buckets)) and set(bucket_mapping)==set(buckets) and
            all(type(source) is str and type(target) is str and
                re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',source) and
                re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',target)
                for source,target in bucket_mapping.items()) and
            len(set(bucket_mapping.values()))==len(bucket_mapping),
            'FORMAL_S3_BUCKET_MAPPING_INVALID')
    return dict(bucket_mapping)


def restore_s3_versions(client,source,evidence,*,bucket_mapping,source_inventory_sha256,
                        source_export_receipt_sha256,timeout=7200):
    """Restore into explicitly prepared empty versioned isolated buckets only.

    Caller supplies the complete explicit bucket mapping and approved export
    digests. Source bytes remain unchanged. Client supplies empty_versioned,
    put_version, delete_marker, content and
    versions. Original version IDs are mapped, never represented as preserved.
    Unsupported encryption/storage protection fails before writes. Valid
    retention/legal hold require an enabled target and exact readback.
    This finite proof does not prove application usability or bucket policy.
    """
    require(type(timeout) is int and 0<timeout<=7200,'FORMAL_S3_TIMEOUT_INVALID')
    source=Path(source).absolute();target=safe_file(evidence)
    require(source.is_dir() and not source.is_symlink() and source.resolve()==source,'FORMAL_SNAPSHOT_PATH_INVALID')
    require(source!=target and source not in target.parents,'FORMAL_S3_RESTORE_PATH_INVALID')
    target.mkdir(mode=0o700);started=time.monotonic()
    def budget():require(time.monotonic()-started<timeout,'FORMAL_S3_RESTORE_TIMEOUT')
    def write(path,raw):
        with path.open('xb') as f:os.chmod(path,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
    def read(path,limit):
        with _existing_file(path).open('rb') as f:raw=f.read(limit+1)
        require(len(raw)<=limit,'FORMAL_S3_RESTORE_FILE_TOO_LARGE');return raw
    def file_identity(path):
        value=_existing_file(path).stat()
        return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
    try:
        raw=read(source/'versions.jsonl',256*1024*1024)
        inventory_identity=file_identity(source/'versions.jsonl')
        receipt_raw=read(source/'export-receipt.json',16384);receipt=_strict_json(receipt_raw)
        require(all(type(value) is str and re.fullmatch('[0-9a-f]{64}',value)
                    for value in (source_inventory_sha256,source_export_receipt_sha256)) and
                hashlib.sha256(raw).hexdigest()==source_inventory_sha256 and
                hashlib.sha256(receipt_raw).hexdigest()==source_export_receipt_sha256,
                'FORMAL_S3_APPROVED_EXPORT_CHANGED')
        require(type(receipt) is dict and set(receipt)=={'buckets','state','inventoryBytes','inventorySha256','versionCount','deleteMarkerCount','totalVersionBytes','uniqueContentCount','multipartObservationsSha256'} and
                receipt.get('state')=='S3_EXPORTED_PENDING_RESTORE_PROOF' and
                receipt.get('inventoryBytes')==len(raw) and
                receipt.get('inventorySha256')==hashlib.sha256(raw).hexdigest(),
                'FORMAL_S3_EXPORT_BINDING_INVALID')
        rows=[_strict_json(line) for line in raw.splitlines()];groups={};identities=set()
        bucket_list=receipt['buckets']
        require(type(bucket_list) is list and bucket_list and all(type(b) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',b) for b in bucket_list) and
                len(bucket_list)==len(set(bucket_list)),'FORMAL_S3_BUCKETS_INVALID')
        buckets=set(bucket_list)
        multipart_raw=read(source/'multipart-observations.json',2*1024*1024)
        require(type(receipt['multipartObservationsSha256']) is str and
                re.fullmatch('[0-9a-f]{64}',receipt['multipartObservationsSha256']) and
                hashlib.sha256(multipart_raw).hexdigest()==receipt['multipartObservationsSha256'],
                'FORMAL_S3_MULTIPART_ORIGINAL_CHANGED')
        multipart=_strict_json(multipart_raw)
        require(type(multipart) is dict and set(multipart)=={'state','before','after'} and
                multipart['state']=='MULTIPART_EMPTY_POINT_OBSERVATIONS','FORMAL_S3_MULTIPART_LIST_INVALID')
        for name in ('before','after'):
            observations=multipart[name]
            require(type(observations) is list and len(observations)==len(bucket_list),
                    'FORMAL_S3_MULTIPART_LIST_INVALID')
            for bucket,value in zip(bucket_list,observations):_require_empty_multipart_observation(value,bucket)
        bucket_mapping=validate_bucket_mapping(bucket_mapping,bucket_list)
        bucket_mapping_sha=hashlib.sha256(_canonical_bytes(bucket_mapping)).hexdigest()
        target_buckets=set(bucket_mapping.values())
        for key in ('inventoryBytes','versionCount','deleteMarkerCount','totalVersionBytes','uniqueContentCount'):
            require(type(receipt[key]) is int and receipt[key]>=0,'FORMAL_S3_EXPORT_BINDING_INVALID')
        require(len(rows)<=500000,'FORMAL_S3_LIST_TOO_LARGE')
        versions=markers=0;total=0;unique=set();protected_buckets=set()
        for row in rows:
            budget()
            require(type(row) is dict and row.get('kind') in ('version','delete-marker') and
                all(type(row.get(k)) is str and row[k] and '\0' not in row[k] for k in ('bucket','key','versionId')) and
                re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',row['bucket']) and
                type(row.get('isLatest')) is bool,'FORMAL_S3_RESTORE_RECORD_INVALID')
            identity=(row['bucket'],row['key'],row['versionId'])
            require(identity not in identities,'FORMAL_S3_VERSION_DUPLICATE');identities.add(identity)
            require(row['bucket'] in buckets,'FORMAL_S3_BUCKETS_INVALID');group=groups.setdefault(identity[:2],[])
            require(row['isLatest']==(len(group)==0),'FORMAL_S3_VERSION_ORDER_INVALID');group.append(row)
            if row['kind']=='delete-marker':markers+=1;continue
            sha=row.get('sha256');headers=row.get('headers')
            require(type(sha) is str and re.fullmatch('[0-9a-f]{64}',sha) and type(row.get('size')) is int and row['size']>=0 and
                row.get('repositoryPath')=='objects/sha256/'+sha[:2]+'/'+sha+'.bin' and type(headers) is dict,
                'FORMAL_S3_RESTORE_RECORD_INVALID')
            if _restore_metadata(headers):protected_buckets.add(row['bucket'])
            actual,size=_hash_object(_existing_file(source/row['repositoryPath']))
            require(actual=='sha256:'+sha and size==row['size'],'FORMAL_S3_RESTORE_CONTENT_CHANGED')
            versions+=1;total+=size;unique.add(sha)
        require(receipt.get('versionCount')==versions and receipt.get('deleteMarkerCount')==markers and
            receipt.get('totalVersionBytes')==total and receipt.get('uniqueContentCount')==len(unique),
            'FORMAL_S3_EXPORT_BINDING_INVALID')
        for bucket in sorted(buckets):
            target_bucket=bucket_mapping[bucket]
            budget();require(client.empty_versioned(target_bucket) is True,'FORMAL_S3_RESTORE_TARGET_NOT_EMPTY_VERSIONED')
            if bucket in protected_buckets:
                require(callable(getattr(client,'replica_configuration',None)) and
                    client.replica_configuration(target_bucket,'object-lock').get('enabled') is True,
                    'FORMAL_S3_RESTORE_OBJECT_LOCK_REQUIRED')
        expected={bucket:{} for bucket in target_buckets};restored_ids=set();sequence=0
        with (target/'version-mapping.jsonl').open('xb') as output:
            os.chmod(target/'version-mapping.jsonl',0o600)
            for (bucket,key),group in groups.items():
                target_bucket=bucket_mapping[bucket]
                for row in reversed(group):
                    budget();sequence+=1
                    require(file_identity(source/'versions.jsonl')==inventory_identity and read(source/'export-receipt.json',16384)==receipt_raw and
                            read(source/'multipart-observations.json',2*1024*1024)==multipart_raw,
                            'FORMAL_S3_EXPORT_CHANGED')
                    base={'sourceBucket':bucket,'targetBucket':target_bucket,'key':key,'kind':row['kind'],
                          'sourceVersionId':row['versionId'],'isLatest':row['isLatest']}
                    write(target/('intent-%06d.json'%sequence),_canonical_bytes(base))
                    if row['kind']=='delete-marker':version=client.delete_marker(target_bucket,key)
                    else:
                        path=_existing_file(source/row['repositoryPath']);actual,size=_hash_object(path)
                        require(actual=='sha256:'+row['sha256'] and size==row['size'],'FORMAL_S3_RESTORE_CONTENT_CHANGED')
                        version=client.put_version(target_bucket,key,path,row['headers'],size,row['sha256'])
                    require(type(version) is str and version and version!='null' and '\0' not in version and
                        (target_bucket,key,version) not in restored_ids,'FORMAL_S3_RESTORE_VERSION_INVALID')
                    restored_ids.add((target_bucket,key,version))
                    mapping=dict(base,targetVersionId=version)
                    # Retain acknowledged write mapping before readback; never retry ambiguity.
                    output.write(_canonical_bytes(mapping));output.flush();os.fsync(output.fileno())
                    expected[target_bucket][(key,version)]={'kind':row['kind'],'isLatest':row['isLatest']}
                    if row['kind']=='version':
                        response,headers=client.content(target_bucket,key,version)
                        try:
                            require(headers.get('x-amz-version-id')==version and headers.get('content-length')==str(row['size']) and
                                all(headers.get(k)==v for k,v in row['headers'].items()),'FORMAL_S3_RESTORE_METADATA_CHANGED')
                            digest=hashlib.sha256();count=0
                            while True:
                                budget();chunk=response.read(1024*1024)
                                if not chunk:break
                                count+=len(chunk);require(count<=row['size'],'FORMAL_S3_RESTORE_READBACK_CHANGED');digest.update(chunk)
                        finally:response.close()
                        require(count==row['size'] and digest.hexdigest()==row['sha256'],'FORMAL_S3_RESTORE_READBACK_CHANGED')
        for bucket in sorted(target_buckets):
            observed={};cursor=None;cursors=set()
            while True:
                budget();page,next_cursor=client.versions(bucket,cursor)
                for row in page:
                    identity=(row['key'],row['versionId']);require(identity not in observed,'FORMAL_S3_VERSION_DUPLICATE')
                    observed[identity]={'kind':row['kind'],'isLatest':row['isLatest']}
                    require(len(observed)<=500000,'FORMAL_S3_LIST_TOO_LARGE')
                if next_cursor is None:break
                require(next_cursor not in cursors,'FORMAL_S3_CURSOR_INVALID');cursors.add(next_cursor);cursor=next_cursor
            require(observed==expected[bucket],'FORMAL_S3_RESTORE_LIST_CHANGED')
        require(read(source/'versions.jsonl',256*1024*1024)==raw and read(source/'export-receipt.json',16384)==receipt_raw and
                read(source/'multipart-observations.json',2*1024*1024)==multipart_raw,
                'FORMAL_S3_EXPORT_CHANGED')
        mapping_sha,mapping_size=_hash_object(target/'version-mapping.jsonl')
        result={'state':'VERSIONS_RESTORED_PENDING_APPLICATION_PROOF','versionCount':versions,'deleteMarkerCount':markers,
                'sourceInventorySha256':receipt['inventorySha256'],
                'sourceExportReceiptSha256':source_export_receipt_sha256,
                'bucketMapping':bucket_mapping,'bucketMappingSha256':bucket_mapping_sha,
                'mappingSha256':mapping_sha[7:],'mappingBytes':mapping_size}
        write(target/'restore-receipt.json',_canonical_bytes(result));return result
    except Exception as error:
        code=error.code if isinstance(error,FormalSnapshotError) else 'FORMAL_S3_RESTORE_FAILED'
        write(target/'failed.json',_canonical_bytes({'state':'FAILED_RETAINED','code':code}))
        raise FormalSnapshotError(code) from None
