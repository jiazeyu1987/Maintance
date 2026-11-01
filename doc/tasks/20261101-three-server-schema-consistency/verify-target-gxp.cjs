'use strict';
// Read-only UI verification. Credentials and screenshots stay outside Git.
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { chromium } = require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const root = 'C:/SpugHandoff/release';
const environment=process.argv[2];const expectedTag=process.argv[3];const acceptance=process.argv[4]==='acceptance';
assert(['local','test','prod','backup'].includes(environment),'Registered verification target required');
if(environment!=='local')assert(/^20[0-9]{2}(?:-[0-9]{2}){5}$/.test(expectedTag),'Exact release tag required');
const resultPath=path.join(__dirname,'target-gxp-'+environment+'-'+(expectedTag||'local')+'.json');
let browser;
let phase = 'read-private-configuration';
const report = { time: new Date().toISOString(), scope: 'read-only-gxp-verification', environment, expectedTag, publicationPerformed: false, remoteAccessPerformed: environment!=='local' };
(async () => {
  try {
    const config = JSON.parse(fs.readFileSync(path.join(root, 'executor.private.json'), 'utf8').replace(/^\uFEFF/, ''));
    const source=new URL(environment==='local'?config.gxpConfigurationSourceUrl:config.targets[environment][acceptance?'acceptanceUrl':'entryUrl']);
    if(environment==='local')assert(['localhost','127.0.0.1','[::1]'].includes(source.hostname),'Local source required');
    else assert(source.hostname===config.targets[environment].host,'Registered remote target required');
    assert(!source.username && !source.password && !source.search && !source.hash, 'Clean source URL required');
    report.sourceUrl = source.href;
    const credentials = JSON.parse(fs.readFileSync(config.loginVerification.credentialsFile, 'utf8').replace(/^\uFEFF/, ''));
    assert(['username', 'password', 'tenantName'].every(key => typeof credentials[key] === 'string' && credentials[key]), 'Private credentials unavailable');
    phase = 'launch-real-browser';
    browser = await chromium.launch({ channel: 'chrome', headless: true });
    const context = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
    const page = await context.newPage();
    const unexpectedWrites = [];
    page.on('request', request => { if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) unexpectedWrites.push({method:request.method(),path:new URL(request.url()).pathname}); });
    phase = 'open-registered-login';
    await page.goto(source.origin + '/login?redirect=' + encodeURIComponent('/infra/config/basic'), { waitUntil: 'domcontentloaded', timeout: 45000 });
    const login = page.getByRole('button', { name: '登录', exact: true });
    await login.waitFor({ state: 'visible', timeout: 45000 });
    await page.getByRole('combobox').fill(credentials.tenantName);
    await page.getByRole('option', { name: credentials.tenantName, exact: true }).click();
    await page.getByPlaceholder('请输入用户名', { exact: true }).fill(credentials.username);
    await page.getByRole('textbox', { name: '请输入密码', exact: true }).fill(credentials.password);
    phase = 'submit-real-login';
    const [authResponse] = await Promise.all([
      page.waitForResponse(response => new URL(response.url()).pathname === '/admin-api/system/auth/login' && response.request().method() === 'POST', { timeout: 45000 }),
      login.click()
    ]);
    const auth = await authResponse.json();
    assert(authResponse.status() === 200 && auth.code === 0 && auth.data?.accessToken && !auth.data?.passwordChangeRequired, 'Real authentication failed');
    await page.waitForURL(url => !/\/(login|change-password)(\/|$)/i.test(url.pathname) && !/\/(login|change-password)(\/|\?|$)/i.test(url.hash), { timeout: 45000 });
    await page.locator('.v-layout').waitFor({ state: 'visible', timeout: 45000 });
    report.realPlaywrightLogin = true;
    phase = 'read-gxp-configuration-from-real-page';
    const [configResponse, runtimeResponse] = await Promise.all([
      page.waitForResponse(response => {
        const url = new URL(response.url());
        return url.origin === source.origin && url.pathname === '/admin-api/infra/config/page' && url.searchParams.get('key') === 'system.gxp.audit-mode' && response.request().method() === 'GET';
      }, { timeout: 45000 }),
      page.waitForResponse(response => {
        const url = new URL(response.url());
        return url.origin === source.origin && url.pathname === '/admin-api/system/gxp-audit-event/runtime-mode' && response.request().method() === 'GET';
      }, { timeout: 45000 }),
      page.goto(source.origin + '/infra/config/basic', { waitUntil: 'domcontentloaded', timeout: 45000 })
    ]);
    const saved = await configResponse.json();
    const runtime = await runtimeResponse.json();
    assert(configResponse.status() === 200 && saved.code === 0, 'Saved configuration unreadable');
    assert(runtimeResponse.status() === 200 && runtime.code === 0, 'Runtime mode unreadable');
    const rows = saved.data?.list?.filter(row => row.key === 'system.gxp.audit-mode');
    assert(rows?.length === 1 && rows[0].visible === true && rows[0].type === 1, 'Unique saved mode required');
    report.savedMode = rows[0].value;
    report.runtimeMode = runtime.data?.mode;
    report.auditEnabled = runtime.data?.auditEnabled;
    report.pendingRestart = report.savedMode !== report.runtimeMode;
    const panel = page.getByTestId('gxp-mode-setting');
    await panel.locator('.el-form-item').filter({ hasText: '已保存模式' }).waitFor({ state: 'visible', timeout: 45000 });
    await panel.locator('.el-loading-mask').waitFor({ state: 'hidden', timeout: 45000 });
    await panel.scrollIntoViewIfNeeded();
    report.savedClosedVisible = (await panel.locator('.el-form-item').filter({ hasText: '已保存模式' }).innerText()).includes('关闭审计');
    report.runtimeClosedVisible = (await panel.locator('.el-form-item').filter({ hasText: '当前运行模式' }).innerText()).includes('关闭审计');
    const privateEvidence = path.join(root, 'private/acceptance/schema-20261101/'+environment+'-gxp');
    fs.mkdirSync(privateEvidence, { recursive: true });
    report.privateScreenshotPath = path.join(privateEvidence, 'gxp-mode-' + Date.now() + '.png');
    await page.screenshot({ path: report.privateScreenshotPath, fullPage: false, mask: [page.locator('input')] });
    report.unexpectedWriteRequests = unexpectedWrites;
    phase = 'assert-saved-and-running-closed';
    assert(report.savedMode === 'DEVELOPMENT_DISABLED', 'Saved GxP mode is not closed');
    assert(report.runtimeMode === 'DEVELOPMENT_DISABLED' && report.auditEnabled === false, 'Actual GxP mode is not closed');
    assert(!report.pendingRestart && report.savedClosedVisible && report.runtimeClosedVisible, 'UI evidence is inconsistent');
    assert(unexpectedWrites.every(r => r.method === 'POST' && ['/admin-api/system/captcha/get','/admin-api/system/captcha/check','/admin-api/system/auth/login','/admin-api/workbench/context'].includes(r.path)), 'Unexpected non-read request detected');
    if(environment!=='local'){phase='verify-exact-frontend-version';const metadata=await page.request.get(source.origin+'/release-info.json');assert(metadata.status()===200,'Frontend version unreadable');const info=await metadata.json();assert(info.releaseTag===expectedTag,'Frontend release tag differs');report.releaseTag=info.releaseTag;}
    report.status = 'PASS';
  } catch (error) {
    report.status = 'FAIL';
    report.failedPhase = phase;
    report.errorCategory = error.name;
    const privateFailure=path.join(root,'private/acceptance/schema-20261101',environment+'-gxp-failure.private.log');
    fs.writeFileSync(privateFailure,String(error.stack||error),'utf8');
    const message=String(error.message||'');
    report.failureSignals={strictLocator:message.includes('strict mode violation'),timeout:message.includes('Timeout'),
      navigationAborted:message.includes('ERR_ABORTED'),targetClosed:message.includes('Target page'),
      notFound:message.includes('404'),forbidden:message.includes('403'),netError:message.includes('net::')};
    // Raw browser errors/responses may include credentials. Never print them.
    process.exitCode = 1;
  } finally {
    if (browser) {
      try { await browser.close(); }
      catch (_) { report.status = 'FAIL'; report.cleanupFailure = true; process.exitCode = 1; }
    }
    fs.writeFileSync(resultPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(report));
  }
})();
