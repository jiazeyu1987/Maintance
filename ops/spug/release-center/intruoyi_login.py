"""Real frontend login through a fresh Playwright CLI browser session.

Only the UI submits credentials. CLI output is captured, never logged or included
in errors. The script and incidental browser logs live beside the private
credentials, while the public evidence contains only an explicit safe whitelist.
"""
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit, urlunsplit
import uuid


class LoginVerificationError(RuntimeError):
    """A sanitized technical-login failure, safe for release job logs."""


_SCRIPT = r'''async (page) => {
  const input = __INPUT__;
  const origin = new URL(input.target).origin;
  const loginPath = '/admin-api/system/auth/login';
  await page.goto(input.target, {waitUntil: 'domcontentloaded', timeout: 45000});
  const login = page.getByRole('button', {name: '登录', exact: true});
  await login.waitFor({state: 'visible', timeout: 45000});
  await page.getByRole('combobox').fill(input.credentials.tenantName);
  await page.getByRole('option', {name: input.credentials.tenantName, exact: true}).click();
  await page.getByPlaceholder('请输入用户名', {exact: true}).fill(input.credentials.username);
  await page.getByRole('textbox', {name: '请输入密码', exact: true}).fill(input.credentials.password);
  const [response] = await Promise.all([
    page.waitForResponse(response => {
      const url = new URL(response.url());
      return url.origin === origin && url.pathname === loginPath &&
        response.request().method() === 'POST';
    }, {timeout: 45000}),
    login.click()
  ]);
  const submitted = response.request().postDataJSON();
  const body = await response.json();
  const userId = Number(body.data && body.data.userId);
  if (response.status() !== 200 || body.code !== 0 ||
      submitted.username !== input.credentials.username ||
      typeof body.data.accessToken !== 'string' || !body.data.accessToken ||
      !Number.isSafeInteger(userId) || userId <= 0 || body.data.passwordChangeRequired === true)
    throw new Error('Authentication was not established');
  await page.waitForURL(url => url.origin === origin &&
    !/\/(login|change-password)(\/|$)/i.test(url.pathname) &&
    !/\/(login|change-password)(\/|\?|$)/i.test(url.hash), {timeout: 45000});
  await page.locator('.v-layout').waitFor({state: 'visible', timeout: 45000});
  await login.waitFor({state: 'hidden', timeout: 45000});
  let gxpAuditMode;
  if (input.readGxpMode) {
    const [configResponse] = await Promise.all([
      page.waitForResponse(response => {
        const url = new URL(response.url());
        return url.origin === origin && url.pathname === '/admin-api/infra/config/page' &&
          url.searchParams.get('key') === 'system.gxp.audit-mode' && response.request().method() === 'GET';
      }, {timeout: 45000}),
      page.goto(origin + '/infra/config/basic', {waitUntil: 'domcontentloaded', timeout: 45000})
    ]);
    const config = await configResponse.json();
    const rows = config.data?.list?.filter(row => row.key === 'system.gxp.audit-mode');
    if (configResponse.status() !== 200 || config.code !== 0 || rows?.length !== 1 ||
        rows[0].visible !== true || rows[0].type !== 1 ||
        !['FORMAL', 'DEVELOPMENT_DISABLED'].includes(rows[0].value))
      throw new Error('A unique saved server GxP mode is required');
    const modePanel = page.getByTestId('gxp-mode-setting');
    await modePanel.locator('.el-form-item').filter({hasText: '已保存模式'}).waitFor({state: 'visible', timeout: 45000});
    await modePanel.locator('.el-loading-mask').waitFor({state: 'hidden', timeout: 45000});
    await modePanel.scrollIntoViewIfNeeded();
    gxpAuditMode = rows[0].value;
  }
  const landed = new URL(page.url());
  landed.search = '';
  landed.hash = '';
  await page.screenshot({path: input.screenshot, fullPage: false,
    mask: [page.locator('input[type="password"]')]});
  return {authenticated: true, authenticationResponseObserved: true,
    authenticatedUserId: userId, authenticatedShellVisible: true, landedUrl: landed.href, gxpAuditMode};
}'''


def _url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
            parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('invalid URL')
    # Accessing port also validates malformed ports.
    parsed.port
    return parsed


def _origin(parsed):
    return parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)


def _cli(node, cli, session, private_dir, *arguments):
    try:
        result = subprocess.run(
            [str(node), str(cli), '-s=' + session, '--json', *arguments],
            cwd=str(private_dir), capture_output=True, timeout=200,
            encoding='utf-8', errors='replace', check=False)
        if result.returncode:
            raise ValueError('CLI failed')
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict) or payload.get('isError') or payload.get('error'):
            raise ValueError('CLI failed')
        return payload
    except Exception:
        raise LoginVerificationError('Playwright login verification failed during ' + arguments[0]) from None


def verify_login(config, target_url, evidence_dir, binding, *, read_gxp_mode=False):
    """Verify UI login; raise a credential-free error on any failed prerequisite.

    loginVerification requires nodePath, cliPath and credentialsFile. The latter
    is private UTF-8 JSON with username/password/tenantName. Binding is exactly
    jobId/env/releaseTag/packageSha256. No authenticated browser state is reused.
    """
    try:
        settings = config['loginVerification']
        node, cli, credentials_file = (Path(settings[key]).resolve(strict=True)
                                       for key in ('nodePath', 'cliPath', 'credentialsFile'))
        if not all(path.is_file() for path in (node, cli, credentials_file)):
            raise ValueError('missing file')
        credentials = json.loads(credentials_file.read_text(encoding='utf-8-sig'))
        credentials = {key: credentials[key] for key in ('username', 'password', 'tenantName')}
        if not all(isinstance(value, str) and value for value in credentials.values()):
            raise ValueError('invalid credentials')
        source_binding = (isinstance(binding, dict) and set(binding) == {'jobId', 'gitCommit'} and
                          isinstance(binding['jobId'], str) and bool(binding['jobId']) and
                          isinstance(binding['gitCommit'], str) and
                          re.fullmatch(r'[0-9a-f]{40}', binding['gitCommit']))
        if read_gxp_mode and not source_binding:
            raise ValueError('invalid source configuration binding')
        if not read_gxp_mode and (not isinstance(binding, dict) or set(binding) != {'jobId', 'env', 'releaseTag', 'packageSha256'} or
                not all(isinstance(value, str) and value for value in binding.values()) or
                binding['env'] not in ('test', 'rehearsal', 'prod', 'backup') or
                not re.fullmatch(r'[0-9a-fA-F]{64}', binding['packageSha256'])):
            raise ValueError('invalid binding')
        target = _url(target_url)
        evidence = Path(evidence_dir).resolve()
        evidence.mkdir(parents=True, exist_ok=True)
    except Exception:
        raise LoginVerificationError('Login verification prerequisites are missing or invalid') from None

    session = 'release-login-' + uuid.uuid4().hex
    screenshot = evidence / (session + '.png')
    evidence_path = evidence / (session + '.json')
    script = None
    private_dir = None
    failure = None
    verified = None
    try:
        private_dir = Path(tempfile.mkdtemp(prefix=session + '-', dir=credentials_file.parent))
        script = private_dir / 'login.private.js'
        script.write_text(_SCRIPT.replace('__INPUT__', json.dumps({
            'credentials': credentials, 'target': target_url, 'screenshot': str(screenshot),
            'readGxpMode': read_gxp_mode,
        }, ensure_ascii=True)), encoding='utf-8')
        _cli(node, cli, session, private_dir, 'open', 'about:blank')
        payload = _cli(node, cli, session, private_dir, 'run-code', '--filename', str(script))
        verified = json.loads(payload['result'])
        landed = _url(verified['landedUrl'])
        if (verified.get('authenticated') is not True or
                verified.get('authenticationResponseObserved') is not True or
                verified.get('authenticatedShellVisible') is not True or
                type(verified.get('authenticatedUserId')) is not int or verified['authenticatedUserId'] <= 0 or
                _origin(landed) != _origin(target) or
                re.search(r'/(login|change-password)(/|$)', landed.path, re.I) or
                not screenshot.is_file() or screenshot.stat().st_size == 0):
            raise ValueError('authentication evidence invalid')
        if read_gxp_mode and verified.get('gxpAuditMode') not in ('FORMAL', 'DEVELOPMENT_DISABLED'):
            raise ValueError('saved GxP mode evidence invalid')
    except Exception:
        failure = 'Real frontend login or its authentication evidence could not be verified'
    finally:
        if private_dir is not None:
            try:
                _cli(node, cli, session, private_dir, 'close')
            except Exception:
                failure = 'Login verification browser cleanup failed'
        if script is not None:
            try:
                script.unlink(missing_ok=True)
            except Exception:
                failure = 'Login verification private script cleanup failed'
    if failure:
        raise LoginVerificationError(failure) from None

    result = {
        'status': 'passed', 'authenticated': True,
        'authenticationResponseObserved': True, 'authenticatedShellVisible': True,
        'authenticatedUserId': verified['authenticatedUserId'],
        'landedUrl': urlunsplit(landed), 'binding': dict(binding),
        'evidencePath': str(evidence_path), 'screenshotPath': str(screenshot),
    }
    if read_gxp_mode:
        result['gxpAuditMode'] = verified['gxpAuditMode']
    try:
        evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        raise LoginVerificationError('Login verification evidence could not be saved') from None
    return result
