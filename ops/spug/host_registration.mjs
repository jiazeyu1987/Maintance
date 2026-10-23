// Owned host registration: real Spug UI; never upload a new key or log credentials.
import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
const require = createRequire('E:/IntRuoyi/IntRuoyiFronted/package.json');
const { chromium } = require('playwright');
const output = 'doc/tasks/20261010-spug-integration';
const admin = JSON.parse(await readFile('E:/Int/CacheData/IntRuoyi/spug-integration-20261010/admin.private.json', 'utf8'));
const mode = process.argv[2] || 'inspect';
const browser = await chromium.launch({channel: 'msedge', headless: true});
const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
page.setDefaultTimeout(12000);
let hostHeaders;
page.on('request', r => {if (r.url().endsWith('/api/host/') && r.method() === 'GET') hostHeaders = r.headers();});
try {
  await page.goto('http://127.0.0.1:18080/', {waitUntil: 'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);
  await page.getByPlaceholder('请输入密码').fill(admin.password);
  await page.getByRole('button', {name: '登 录'}).click();
  const warning = page.getByRole('button', {name: '知道了'});
  await warning.waitFor({state: 'visible'});
  await warning.click();
  await warning.waitFor({state: 'hidden'});
  await page.getByText('工作台', {exact: true}).first().waitFor();
  const initialLoad = page.waitForResponse(r => r.url().endsWith('/api/host/') && r.request().method() === 'GET');
  await page.getByText('主机管理', {exact: true}).first().click();
  let listedHosts = (await (await initialLoad).json()).data;
  await page.getByText('Default', {exact: true}).first().click();
  await page.getByRole('button', {name: /新建|添加主机/}).first().waitFor();
  const listing = await page.locator('body').innerText();
  await page.screenshot({path: output + '/hosts-list-before-20261014.png', fullPage: true});
  if (mode === 'register') {
    const config = JSON.parse(await readFile('E:/IntRuoyi/IntRuoyiBackend/script/backup-ops/config/backup-ops.config.json', 'utf8'));
    const secrets = JSON.parse(await readFile('E:/IntRuoyi/IntRuoyiBackend/script/backup-ops/config/backup-ops.secrets.json', 'utf8'));
    const definitions = [
      {role: 'TEST', key: 'test', name: 'IntRuoyi 测试服', expected: '172.30.30.58'},
      {role: 'BACKUP', key: 'backup', name: 'IntRuoyi 备份服', expected: '172.30.30.59'},
      {role: 'PROD', key: 'production', name: 'IntRuoyi 正式服', expected: '172.30.30.57'},
    ];
    if (secrets.ssh.user !== 'root' || secrets.ssh.port !== 22) throw new Error('Previously verified SSH identity changed; registration stopped.');
    const results = [];
    for (const def of definitions) {
      const address = config.servers[def.key]?.host;
      if (address !== def.expected) throw new Error('Existing role mapping changed; registration stopped.');
      const existing = listedHosts.filter(h => h.hostname === address && h.port === secrets.ssh.port);
      if (existing.length > 1) throw new Error('Duplicate address needs current port/identity adjudication; no new host saved.');
      let row = page.getByRole('row').filter({has: page.getByText(def.name, {exact: true})});
      if (!existing.length) {
        await page.getByRole('button', {name: /新建/}).first().click();
        await page.getByText('新建主机', {exact: true}).click();
        const dialog = page.getByRole('dialog');
        await dialog.getByPlaceholder('请输入主机名称').fill(def.name);
        await dialog.getByPlaceholder('用户名', {exact: true}).fill(secrets.ssh.user);
        await dialog.getByPlaceholder('主机名/IP', {exact: true}).fill(address);
        await dialog.getByPlaceholder('端口', {exact: true}).fill(String(secrets.ssh.port));
        // Independent key path only: installed Spug calls SSH.ping(), not add_public_key().
        await dialog.locator('input[type=file]').setInputFiles('C:/Users/BJB110/.ssh/id_rsa');
        await dialog.getByPlaceholder('请输入主机备注信息').fill(def.role + '；沿用现有认证；仅登记及只读连接核验，部署另按批准流程。');
        const saved = page.waitForResponse(r => r.url().endsWith('/api/host/') && r.request().method() === 'POST');
        await dialog.getByRole('button', {name: /验\s*证/}).click();
        const body = await (await saved).json();
        if (body.error || !body.data?.id) throw new Error('Spug host save/authentication failed; no credential data logged.');
        await dialog.waitFor({state: 'hidden'});
        results.push({role: def.role, name: body.data.name, ip: body.data.hostname,
          port: body.data.port, username: body.data.username, hostId: body.data.id,
          groupIds: body.data.group_ids, saved: true, isVerified: body.data.is_verified,
          existingEntryReused: false, sshVerification: 'SPUG_INDEPENDENT_KEY_PING_PASSED',
          remoteAuthorizedKeysModified: false});
      } else {
        if (existing[0].name !== def.name || existing[0].username !== secrets.ssh.user)
          throw new Error('Existing role/name/user differs; no duplicate or overwrite performed.');
        results.push({role: def.role, name: def.name, ip: address, port: secrets.ssh.port,
          username: secrets.ssh.user, existingEntryReused: true});
      }
      const reloadLoad = page.waitForResponse(r => r.url().endsWith('/api/host/') && r.request().method() === 'GET');
      await page.reload({waitUntil: 'domcontentloaded'});
      listedHosts = (await (await reloadLoad).json()).data;
      await page.getByText('Default', {exact: true}).first().click();
      row = page.getByRole('row').filter({has: page.getByText(def.name, {exact: true})});
      await row.getByText(def.name, {exact: true}).waitFor();
      await row.getByText('编辑', {exact: true}).click();
      const edit = page.getByRole('dialog');
      const readback = {
        name: await edit.getByPlaceholder('请输入主机名称').inputValue(),
        ip: await edit.getByPlaceholder('主机名/IP', {exact: true}).inputValue(),
        username: await edit.getByPlaceholder('用户名', {exact: true}).inputValue(),
        port: Number(await edit.getByPlaceholder('端口', {exact: true}).inputValue()),
        group: await edit.locator('.ant-select-selection-item').innerText(),
      };
      if (readback.name !== def.name || readback.ip !== address || readback.username !== secrets.ssh.user || readback.port !== secrets.ssh.port)
        throw new Error('Saved/reopened host fields differ from approved existing configuration.');
      results[results.length - 1].uiReadback = readback;
      await edit.getByRole('button', {name: /取\s*消/}).click();
      await edit.waitFor({state: 'hidden'});
    }
    if (!hostHeaders) throw new Error('Final host-list authentication context unavailable.');
    const independent = await page.request.get('http://127.0.0.1:18080/api/host/', {headers: hostHeaders});
    const original = await independent.json();
    if (original.error || !Array.isArray(original.data)) throw new Error('Final read-only host API shape mismatch.');
    for (const result of results) {
      const matches = original.data.filter(h => h.hostname === result.ip && h.port === result.port && h.username === result.username);
      if (matches.length !== 1 || matches[0].name !== result.name || matches[0].is_verified !== true)
        throw new Error('Final independent host identity/SSH verification mismatch.');
      result.hostId = matches[0].id;
      result.groupIds = matches[0].group_ids;
      result.saved = true;
      result.isVerified = true;
      result.sshVerification = 'SPUG_INDEPENDENT_KEY_PING_PASSED';
      result.remoteAuthorizedKeysModified = false;
      result.apiReadbackPassed = true;
    }
    const evidence = {observedAt: new Date().toISOString(), status: 'THREE_HOSTS_REGISTERED_REAL_UI_AND_SSH_VERIFIED',
      rolesFromExistingConfiguration: true, credentialValuesRecorded: false,
      newRemoteAccountsOrKeys: false, deploymentTriggered: false, results};
    await page.screenshot({path: output + '/hosts-registered-20261014.png', fullPage: true});
    await writeFile(output + '/hosts-registration-20261014.json', JSON.stringify(evidence, null, 2), 'utf8');
    console.log(JSON.stringify(evidence, null, 2));
    process.exitCode = 0;
  } else {
  await page.getByRole('button', {name: /新建|添加主机/}).first().click();
  await page.locator('.ant-dropdown:not(.ant-dropdown-hidden)').waitFor();
  await page.getByText('新建主机', {exact: true}).click();
  await page.getByRole('dialog').waitFor();
  const form = await page.locator('body').innerText();
  const fields = await page.locator('input,textarea,select').evaluateAll(items => items.map(e => ({
    tag: e.tagName, type: e.type, placeholder: e.placeholder, id: e.id, role: e.getAttribute('role')
  })));
  const evidence = {observedAt: new Date().toISOString(), listing, form, fields, submitted: false};
  await writeFile(output + '/hosts-ui-inspection-20261014.json', JSON.stringify(evidence, null, 2), 'utf8');
  console.log(JSON.stringify(evidence, null, 2));
  }
} finally {
  await browser.close();
}
