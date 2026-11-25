const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const [environment, tag, commit, explicitOrigin] = process.argv.slice(2);
if (!['test', 'prod', 'prod-maintenance'].includes(environment) || !/^\d{4}(-\d{2}){5}$/.test(tag || '') || !/^[0-9a-f]{40}$/.test(commit || '')) throw Error('EXPLICIT_RELEASE_BINDING_REQUIRED');
const host = environment === 'test' ? '172.30.30.58' : '172.30.30.57';
const base = explicitOrigin || `http://${host}:8081`;
if (new URL(base).hostname !== host) throw Error('TARGET_HOST_MISMATCH');
const expected = `http://${host}:18734/`;
const folder = path.join('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125', environment);
fs.mkdirSync(folder, { recursive: true });
const credentials = JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/loginCredentials.json', 'utf8').replace(/^\uFEFF/, ''));
if (credentials.tenantName !== '芋道源码' || credentials.username !== 'admin') throw Error('APPROVED_IDENTITY_REQUIRED');
const safeUrl = value => { const u = new URL(value); return u.origin + u.pathname; };
const result = { environment, releaseTag: tag, sourceCommit: commit, origin: base, startedAt: new Date().toISOString(), checks: [], observations: [], status: 'BLOCKED' };
(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const context = await browser.newContext({ viewport: { width: 1500, height: 1100 }, serviceWorkers: 'block' });
  const page = await context.newPage(); page.setDefaultTimeout(45000);
  const inFlight = new Map(), networkEvents = [];
  context.on('request', request => { inFlight.set(request, { path: safeUrl(request.url()), method: request.method(), startedAt: new Date().toISOString() }); });
  context.on('requestfinished', request => { const item = inFlight.get(request); if (item) networkEvents.push({ ...item, finishedAt: new Date().toISOString() }); inFlight.delete(request); });
  context.on('requestfailed', request => { inFlight.delete(request); });
  const allowed = new Set(['/admin-api/system/auth/login', '/admin-api/system/auth/fenbeitong-assistant-ticket', '/admin-api/system/captcha/get', '/admin-api/system/captcha/check']);
  await context.route('**/*', async route => {
    const request = route.request(), u = new URL(request.url());
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method()) && !allowed.has(u.pathname)) {
      result.observations.push({ kind: 'interception', path: safeUrl(request.url()), method: request.method(), reason: 'predeclared read-only protection' });
      await route.abort('blockedbyclient'); return;
    }
    await route.continue();
  });
  page.on('console', message => { if (message.type() === 'error') result.observations.push({ kind: 'console', message: message.text(), location: message.location() }); });
  page.on('pageerror', error => result.observations.push({ kind: 'pageerror', message: String(error) }));
  page.on('requestfailed', request => result.observations.push({ kind: 'requestfailed', path: safeUrl(request.url()), error: request.failure()?.errorText }));
  let permissions, releaseInfo;
  const reads = [];
  page.on('response', response => {
    const u = new URL(response.url());
    if (response.status() >= 400) result.observations.push({ kind: 'http', path: safeUrl(response.url()), status: response.status() });
    if (u.origin === new URL(expected).origin && u.pathname === '/api/fenbeitong-expense-reimbursement/config') reads.push(response.text().then(body => {
      result.helperConfigReads ||= [];
      result.helperConfigReads.push({ url: response.url(), status: response.status(), body });
    }));
    if (u.pathname.endsWith('/system/auth/get-permission-info')) reads.push(response.json().then(value => { permissions = value; }));
    if (u.pathname.endsWith('/release-info.json')) reads.push(response.json().then(value => { releaseInfo = value; }));
    if (u.pathname.startsWith('/admin-api/') && response.headers()['content-type']?.includes('json')) reads.push(response.json().then(value => {
      if (value.code !== undefined && value.code !== 0 && value.code !== 200) result.observations.push({ kind: 'business', path: u.pathname, code: value.code, message: value.msg });
    }).catch(error => result.observations.push({ kind: 'response-read', path: u.pathname, message: String(error) })));
  });
  try {
    await page.goto(base + '/login?redirect=/index', { waitUntil: 'networkidle' });
    await page.locator('.el-form:visible .el-select input').fill(credentials.tenantName);
    await page.getByRole('option', { name: credentials.tenantName, exact: true }).click();
    await page.getByPlaceholder('请输入用户名', { exact: true }).fill(credentials.username);
    await page.locator('input[type=password]:visible').fill(credentials.password);
    const remember = page.getByRole('checkbox', { name: '记住我', exact: true });
    if (await remember.isChecked()) await remember.uncheck();
    const loginPromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/system/auth/login') && response.request().method() === 'POST');
    await page.getByRole('button', { name: '登录', exact: true }).click();
    const auth = await (await loginPromise).json();
    if (auth.code !== 0 || auth.data?.passwordChangeRequired) throw Error('REAL_LOGIN_FAILED');
    await page.waitForURL(url => !['/login', '/change-password'].includes(url.pathname));
    await page.locator('.el-menu').first().waitFor(); await Promise.all(reads);
    if (permissions?.data?.user?.username !== credentials.username) throw Error('LOGIN_IDENTITY_UNVERIFIED');
    result.checks.push({ name: 'real-login', status: 'PASS', tenant: credentials.tenantName, username: credentials.username });
    const findMenu = nodes => { for (const n of nodes || []) { if ((n.component || '').includes('erp/finance/fenbeitong-voucher')) return n; const child = findMenu(n.children); if (child) return child; } };
    const target = findMenu(permissions.data.menus);
    if (!target) throw Error('FENBEITONG_MENU_PERMISSION_MISSING');
    const statusPromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/system/auth/fenbeitong-assistant/status'));
    const ticketPromise = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/system/auth/fenbeitong-assistant-ticket'));
    const callbackPromise = page.waitForResponse(response => new URL(response.url()).origin === new URL(expected).origin && new URL(response.url()).pathname === '/auth/callback');
    statusPromise.catch(() => {}); ticketPromise.catch(() => {}); callbackPromise.catch(() => {});
    await page.locator('.el-select').filter({ hasText: '请输入菜单内容' }).locator('input').fill('分贝通');
    await page.getByRole('option').filter({ hasText: '分贝通' }).first().click();
    const statusResponse = await statusPromise, status = await statusResponse.json();
    if (!statusResponse.ok() || status.code !== 0 || status.data?.publicUrl !== expected || status.data?.running !== true) throw Error('FENBEITONG_RUNTIME_STATUS_INVALID');
    result.checks.push({ name: 'runtime-public-url', status: 'PASS', publicUrl: status.data.publicUrl });
    const ticketResponse = await ticketPromise, ticket = await ticketResponse.json();
    if (!ticketResponse.ok() || ticket.code !== 0 || !ticket.data?.ticket) throw Error('FENBEITONG_TICKET_FAILED');
    const callbackResponse = await callbackPromise;
    if (callbackResponse.status() >= 400) { result.callbackBody = await callbackResponse.text(); throw Error('FENBEITONG_CALLBACK_HTTP_' + callbackResponse.status()); }
    const iframe = page.locator('iframe[title="分贝通费用报销"]'); await iframe.waitFor({ state: 'visible' });
    const frame = await (await iframe.elementHandle()).contentFrame();
    await frame.waitForURL(url => url.origin === new URL(expected).origin && url.pathname !== '/auth/callback');
    await frame.waitForLoadState('networkidle');
    const assistantBody = await frame.locator('body').innerText();
    if (!assistantBody.includes('分贝通') || /认证失败|没有.*权限/.test(assistantBody)) throw Error('FENBEITONG_AUTHENTICATED_PAGE_INVALID');
    await Promise.all(reads);
    if ((result.helperConfigReads || []).some(read => read.status >= 400)) {
      await frame.getByRole('button', { name: '字段对应关系', exact: true }).click();
      await frame.getByText('尚无已保存配置，当前显示默认字段对应关系。', { exact: true }).waitFor({ state: 'visible' });
      result.helperMappingState = 'NOT_CONFIGURED';
      await page.screenshot({ path: path.join(folder, 'fenbeitong-mapping-state.private.png'), fullPage: true, animations: 'disabled' });
      await frame.locator('#closeFieldMappingButton').click();
    }
    await page.screenshot({ path: path.join(folder, 'fenbeitong-authenticated.private.png'), fullPage: true, animations: 'disabled' });
    result.checks.push({ name: 'real-ticket-and-authenticated-iframe', status: 'PASS', frameUrl: safeUrl(frame.url()), visibleTextLength: assistantBody.length });
    await Promise.all(reads);
    if (inFlight.size !== 0) throw Error('PENDING_PAGE_REQUESTS');
    result.checks.push({ name: 'observed-page-requests-completed', status: 'PASS', pendingRequests: 0 });
    const dock = page.getByTestId('release-info-dock').getByRole('button');
    await dock.waitFor({ state: 'visible' });
    if ((await dock.innerText()).trim() !== tag) throw Error('VISIBLE_RELEASE_TAG_MISMATCH');
    await dock.click(); const dialog = page.locator('.el-dialog:visible');
    await dialog.getByText('版本变更说明', { exact: true }).waitFor();
    const changes = await dialog.locator('.release-info-dialog li').allTextContents();
    if (!changes.length || releaseInfo?.releaseTag !== tag || releaseInfo?.sourceCommit !== commit) throw Error('VERSION_CHANGELOG_BINDING_FAILED');
    result.checks.push({ name: 'visible-version-and-changelog', status: 'PASS', releaseTag: tag, sourceCommit: commit, changes });
    result.assistantBody = assistantBody;
    result.status = result.observations.length ? 'NEEDS_REVIEW' : 'PASS';
  } catch (error) {
    result.error = String(error).replaceAll(credentials.password, '<redacted>').replace(/(https?:\/\/[^\s"<>?]+)\?[^\s"<>]*/g, '$1?<redacted>'); process.exitCode = 1;
  } finally {
    result.endedAt = new Date().toISOString();
    result.inFlight = [...inFlight.values()]; result.recentNetwork = networkEvents.slice(-60);
    result.body = await page.locator('body').innerText().catch(() => '<unavailable>');
    result.frames = await Promise.all(page.frames().map(async frame => ({ url: safeUrl(frame.url()), body: await frame.locator('body').innerText().catch(() => '<unavailable>') })));
    await page.screenshot({ path: path.join(folder, 'fenbeitong-page.private.png'), fullPage: true, animations: 'disabled', mask: [page.locator('input[type=password]')] }).catch(() => {});
    fs.writeFileSync(path.join(folder, 'fenbeitong-page.private.json'), JSON.stringify(result, null, 2), 'utf8');
    console.log(JSON.stringify({ status: result.status, checks: result.checks, observations: result.observations.length, error: result.error }));
    await browser.close();
  }
})().catch(error => { console.error(String(error).replaceAll(credentials.password, '<redacted>')); process.exitCode = 1; });
