"""Explicit application routing for the Spug release bridge; no default upstream."""
import json
import re
import urllib.parse
import urllib.request


class RegistryError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class ApplicationRegistry:
    def __init__(self, config):
        rows = config.get('applications')
        if not isinstance(rows, list) or not rows:
            raise ValueError('Explicit applications registry required')
        self.apps = {}
        endpoints = set()
        for app in rows:
            identity = app.get('id', '')
            if not re.fullmatch(r'[a-z][a-z0-9-]{2,35}', identity) or identity in self.apps:
                raise ValueError('Application id invalid or duplicated')
            if not all(isinstance(app.get(k), str) and app[k].strip() for k in ('name', 'repo', 'scope')):
                raise ValueError('Application name, repository and scope required')
            if app.get('status') == 'ready':
                url = urllib.parse.urlsplit(app.get('executorUrl', ''))
                if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
                    raise ValueError('Explicit executor origin required')
                if not isinstance(app.get('bridgeKey'), str) or not app['bridgeKey']:
                    raise ValueError('Application bridge key required')
                if app['executorUrl'] in endpoints:
                    raise ValueError('Applications cannot share an executor endpoint')
                endpoints.add(app['executorUrl'])
            elif app.get('status') == 'pending':
                if not isinstance(app.get('blockers'), list) or not app['blockers'] or not all(isinstance(x, str) and x.strip() for x in app['blockers']):
                    raise ValueError('Pending application requires explicit blockers')
                if 'executorUrl' in app or 'bridgeKey' in app:
                    raise ValueError('Pending application cannot have an upstream')
            else:
                raise ValueError('Unknown application registration status')
            self.apps[identity] = dict(app)
        self.default = config.get('defaultApplication')
        if self.default not in self.apps:
            raise ValueError('Explicit registered defaultApplication required')
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def catalog(self):
        return dict(defaultApplication=self.default, applications=[{
            k: app[k] for k in ('id', 'name', 'repo', 'scope', 'status', 'blockers') if k in app
        } for app in self.apps.values()])

    def resolve(self, path, method, payload=None):
        match = re.fullmatch(r'/applications/([a-z][a-z0-9-]{2,35})/(state|commits|actions/[a-z-]+)', path)
        if not match:
            raise RegistryError(404, '发布应用路由不存在')
        identity, route = match.groups()
        if identity not in self.apps:
            raise RegistryError(404, '未登记的应用：' + identity)
        app = self.apps[identity]
        if (method == 'GET' and route not in ('state', 'commits')) or (method == 'POST' and not route.startswith('actions/')) or method not in ('GET', 'POST'):
            raise RegistryError(405, '应用操作方法不匹配')
        if app['status'] != 'ready':
            raise RegistryError(409, app['name'] + ' 尚未接入发布执行器：' + '；'.join(app['blockers']))
        if method == 'POST' and (not isinstance(payload, dict) or payload.get('applicationId') != identity):
            raise RegistryError(409, '请求应用身份与当前路由不一致，未执行操作')
        return app, '/' + route

    def request(self, app, route, method, payload, actor):
        headers = {'Content-Type': 'application/json', 'X-Release-Key': app['bridgeKey'], 'X-Release-Actor': actor}
        def send(path, data=None, verb='GET'):
            request = urllib.request.Request(app['executorUrl'] + path, data=data, method=verb, headers=headers)
            return self.http.open(request, timeout=20)

        # Validate the actual executor before forwarding commits or any write.
        # A configuration pointing at another application's process must fail closed.
        with send('/state') as response:
            raw = response.read()
        state = json.loads(raw)
        if state.get('application', {}).get('id') != app['id']:
            raise RegistryError(409, '执行器实际应用身份不符，未转发操作')
        if route == '/state':
            return 200, raw
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if method == 'POST' else None
        with send(route, data, method) as response:
            return response.status, response.read()
