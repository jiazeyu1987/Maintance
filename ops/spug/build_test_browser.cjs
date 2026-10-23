// Real Spug UI operations; never issue a release API request from the driver.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('D:/IntRuoyiWorktree/release-lab-control/IntRuoyiFronted/node_modules/playwright');
const output = 'E:/Int/CacheData/IntRuoyi/tests/releaselab-v1-v4/managed-acceptance-20261014/v4/spug-05/spug-ui';
fs.mkdirSync(output, { recursive: true });
const admin = JSON.parse(fs.readFileSync('E:/Int/CacheData/IntRuoyi/spug-integration-20261010/build-test-spug-login.private.json', 'utf8'));
const mode = process.argv[2];
if (!['configure', 'configure-continuation', 'remove-obsolete-status', 'submit', 'continue', 'status', 'history', 'history-failure', 'inspect'].includes(mode)) throw new Error('SPUG_UI_ACTION_REQUIRED');
const tasks = [
  { name: '构建并发布测试服', mode: 'submit', description: '手动提交固定源码：构建、NAS上传、同包部署测试服、后台真实页面验收。受理不等于成功；本次构建发布结果查看最终结果。禁止激活定时任务。' },
  { name: '本次构建发布结果', mode: 'status', description: '查询本次明确绑定的原构建和部署。仅实际构建、NAS上传、测试服部署及后台验收全部通过，结果才为成功。重复查询不重建、不部署。禁止激活。' }
];
for (const task of tasks) task.command = 'python3 /opt/intruoyi-spug/release_build_test.py --mode ' + task.mode;
if (mode !== 'configure' && mode !== 'submit') {
  tasks[1].command += ' --config /run/intruoyi-spug/build-test-continuation.private.json';
  tasks.push({ name: '继续本次构建发布', mode: 'continue',
    description: '仅继续已绑定的原构建及测试发布，不重新构建、不重放已提交部署。未知写入、失败状态或已有执行器阻塞；查询本次构建发布结果。禁止激活。',
    command: 'python3 /opt/intruoyi-spug/release_build_test.py --mode continue --config /run/intruoyi-spug/build-test-continuation.private.json' });
}
let browser, page;
async function login() {
  browser = await chromium.launch({ headless: true, executablePath: 'E:/Int/DevCache/playwright-browsers/chromium-1223/chrome-win64/chrome.exe' });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(20000);
  page.on('response', response => {
    if (response.request().method() === 'POST' && response.url().includes('/api/account/login')) {
      void response.json().then(body => console.log(JSON.stringify({ loginHttpStatus: response.status(),
        loginError: Boolean(body.error), credentialRejected: /密码|账户|账号|验证/.test(String(body.error)),
        ipWarning: /真实.*IP|real.*IP/.test(String(body.error)), tokenReturned: Boolean(body.data?.access_token || body.data?.token) })));
    }
  });
  await page.goto('http://127.0.0.1:18080/', { waitUntil: 'domcontentloaded' });
  await page.getByPlaceholder('请输入账户').fill(admin.username);
  await page.getByPlaceholder('请输入密码').fill(admin.password);
  await page.getByRole('button', { name: '登 录' }).click();
  const warning = page.getByRole('button', { name: '知道了' });
  const dashboard = page.getByText('工作台', { exact: true }).first();
  await Promise.race([warning.waitFor(), dashboard.waitFor()]);
  if (await warning.isVisible()) { await warning.click(); await warning.waitFor({ state: 'hidden' }); }
  await page.getByText('工作台', { exact: true }).first().waitFor();
  await page.getByText('任务计划', { exact: true }).first().click();
  await page.getByRole('button', { name: /新建/ }).waitFor();
}
const rowFor = task => page.getByRole('row').filter({ has: page.getByText(task.name, { exact: true }) });
async function configure() {
  for (const task of (mode === 'configure-continuation' ? tasks.slice(1) : tasks)) {
    const count = await rowFor(task).count();
    if (count > 1) throw new Error('SPUG_DUPLICATE_TASK_NAME');
    if (count) {
      await rowFor(task).getByText('未激活', { exact: true }).waitFor();
      await rowFor(task).getByText('编辑', { exact: true }).click();
      const edit = page.getByRole('dialog', { name: '编辑任务' });
      if ((await edit.innerText()).includes(task.command)) {
        await edit.getByRole('button', { name: 'Close', exact: true }).click();
        continue;
      }
      if (mode !== 'configure-continuation' || task.name !== '本次构建发布结果'
          || !(await edit.innerText()).includes('python3 /opt/intruoyi-spug/release_build_test.py --mode status')) {
        throw new Error('SPUG_EXISTING_TASK_COMMAND_DIFFERS');
      }
      await edit.locator('.ace_content').click();
      await page.keyboard.press('Control+A'); await page.keyboard.insertText(task.command);
      await edit.getByPlaceholder('请输入模板备注信息').fill(task.description);
      await edit.getByRole('button', { name: '下一步', exact: true }).click();
      await edit.getByRole('button', { name: '下一步', exact: true }).click();
      const response = page.waitForResponse(r => r.url().endsWith('/api/schedule/') && r.request().method() === 'POST');
      await edit.getByRole('button', { name: /提\s*交/ }).click();
      const result = await (await response).json();
      if (result.error) throw new Error('SPUG_OWN_RESULT_CONFIGURE_FAILED');
      await edit.waitFor({ state: 'hidden' });
      await rowFor(task).getByText('未激活', { exact: true }).waitFor();
      continue;
    }
    await page.getByRole('button', { name: /新建/ }).click();
    const dialog = page.getByRole('dialog', { name: '新建任务' });
    await dialog.getByRole('button', { name: '添加类型' }).click();
    const type = page.locator('.ant-modal-confirm').filter({ hasText: '添加任务类型' });
    await type.locator('input').fill('标准发布');
    await type.getByRole('button', { name: /确\s*定/ }).click();
    await dialog.getByPlaceholder('请输入任务名称').fill(task.name);
    await dialog.locator('.ace_content').click();
    await page.keyboard.press('Control+A'); await page.keyboard.insertText(task.command);
    await dialog.getByPlaceholder('请输入模板备注信息').fill(task.description);
    await dialog.getByRole('button', { name: '下一步', exact: true }).click();
    await dialog.getByRole('spinbutton').fill('3600');
    await dialog.getByRole('button', { name: '下一步', exact: true }).click();
    await dialog.getByRole('combobox').click();
    await page.getByText('本机', { exact: true }).last().click();
    const response = page.waitForResponse(r => r.url().endsWith('/api/schedule/') && r.request().method() === 'POST');
    await dialog.getByRole('button', { name: /提\s*交/ }).click();
    const result = await (await response).json();
    if (result.error) throw new Error('SPUG_TASK_CONFIGURE_FAILED');
    await dialog.waitFor({ state: 'hidden' });
    await rowFor(task).getByText('未激活', { exact: true }).waitFor();
  }
  await page.screenshot({ path: path.join(output, mode + '.png'), fullPage: true });
  fs.writeFileSync(path.join(output, mode + '.json'), JSON.stringify({ at: new Date().toISOString(), tasks, activated: false }, null, 2));
}
async function execute(task) {
  const row = rowFor(task);
  await row.getByText('未激活', { exact: true }).waitFor();
  if (['submit', 'continue'].includes(task.mode)) fs.writeFileSync(path.join(output, task.mode + '-click-intent.json'), JSON.stringify({ at: new Date().toISOString(), task: task.name }), { flag: 'wx' });
  await row.getByText('更多', { exact: true }).click();
  await page.getByText('执行测试', { exact: true }).last().click();
  const response = page.waitForResponse(r => r.url().includes('/api/schedule/') && r.request().method() === 'POST', { timeout: 40000 });
  await page.locator('.ant-modal-confirm').filter({ hasText: '操作确认' }).getByRole('button', { name: /确\s*定/ }).click();
  const result = await (await response).json();
  if (result.error || !Number.isInteger(result.data)) throw new Error('SPUG_MANUAL_EXECUTION_RESPONSE_FAILED');
  const info = page.getByRole('dialog', { name: '任务执行详情' });
  await info.getByText(/SUBMITTED_NOT_PASSED|NOT_PASSED|WORKER_NOT_RUNNING|BUILD_NAS_TEST_BROWSER_PASSED|REFUSED_OR_STOPPED|LOCAL_STORAGE_OR_EXECUTION_FAILED/).waitFor();
  const detail = await info.innerText();
  if (['submit', 'continue'].includes(task.mode) && !detail.includes('SUBMITTED_NOT_PASSED')) throw new Error('SPUG_BUILD_SUBMISSION_NOT_ACCEPTED');
  const observation = { at: new Date().toISOString(), task: task.name, historyId: result.data,
    accepted: detail.includes('SUBMITTED_NOT_PASSED'), passed: detail.includes('BUILD_NAS_TEST_BROWSER_PASSED'), detail };
  fs.writeFileSync(path.join(output, task.mode + '-' + result.data + '.json'), JSON.stringify(observation, null, 2), { flag: 'wx' });
  await info.screenshot({ path: path.join(output, task.mode + '-' + result.data + '.png') });
  console.log(JSON.stringify({ task: task.name, historyId: result.data, accepted: observation.accepted, passed: observation.passed, detail }));
}
async function removeObsoleteStatus() {
  // Both rows were created by this task. Only ID 6 is the unused original query entry.
  const row = page.locator('tr[data-row-key="6"]');
  await row.getByText('本次构建发布结果', { exact: true }).waitFor();
  await row.getByText('未激活', { exact: true }).waitFor();
  await row.getByText('编辑', { exact: true }).click();
  const edit = page.getByRole('dialog', { name: '编辑任务' });
  const detail = await edit.innerText();
  if (!detail.includes('python3 /opt/intruoyi-spug/release_build_test.py --mode status')
      || detail.includes('--config')) throw new Error('OBSOLETE_OWN_QUERY_IDENTITY_CHANGED');
  fs.writeFileSync(path.join(output, 'obsolete-query-6.json'), JSON.stringify({ at: new Date().toISOString(), taskId: 6, detail,
    reason: 'Unused own query task replaced by explicit original-continuation query.', executionHistoryCount: 0 }, null, 2), { flag: 'wx' });
  await edit.getByRole('button', { name: 'Close', exact: true }).click();
  await row.getByText('更多', { exact: true }).click();
  await page.getByText('删除', { exact: true }).last().click();
  const response = page.waitForResponse(r => r.url().includes('/api/schedule/') && r.request().method() === 'DELETE');
  await page.locator('.ant-modal-confirm').filter({ hasText: '删除确认' }).getByRole('button', { name: /确\s*定/ }).click();
  const actual = await response;
  if (new URL(actual.url()).searchParams.get('id') !== '6' || (await actual.json()).error) throw new Error('OBSOLETE_OWN_QUERY_DELETE_FAILED');
  await row.waitFor({ state: 'hidden' });
  if (await rowFor(tasks[1]).count() !== 1) throw new Error('SPUG_RESULT_QUERY_STILL_AMBIGUOUS');
  console.log('Removed only unused own query task 6; original submission and continuation histories preserved.');
}
async function history() {
  const failed = mode === 'history-failure';
  const wanted = tasks[1];
  const row = rowFor(wanted);
  await row.getByText('更多', { exact: true }).click();
  await page.getByText('历史记录', { exact: true }).last().click();
  const history = page.getByRole('dialog', { name: '任务执行记录 - ' + wanted.name });
  await history.getByText('详情', { exact: true }).first().click();
  const info = page.getByRole('dialog', { name: '任务执行详情' });
  await info.getByText(failed ? 'RELEASE_WORKFLOW_APPLICATION_BROWSER_ACCEPTANCE_FAILED' : 'BUILD_NAS_TEST_BROWSER_PASSED', { exact: false }).waitFor();
  const detail = await info.innerText();
  if (!detail.includes(failed ? '返回状态： 2' : '返回状态： 0')) throw new Error('SPUG_PERSISTENT_RESULT_STATUS_MISMATCH');
  const name = failed ? 'fresh-login-failed-history' : 'fresh-login-history';
  fs.writeFileSync(path.join(output, name + '.json'), JSON.stringify({ at: new Date().toISOString(), detail, readAfterFreshLogin: true, releaseResubmitted: false, releasePassed: !failed }, null, 2), { flag: 'wx' });
  await info.screenshot({ path: path.join(output, name + '.png') });
  console.log(failed ? 'Fresh-login Spug history retains the actual failed browser gate; no release re-execution.' : 'Fresh-login Spug historical result passed; no release re-execution.');
}
async function main() {
  await login();
  if (['configure', 'configure-continuation'].includes(mode)) await configure();
  else if (mode === 'remove-obsolete-status') await removeObsoleteStatus();
  else if (mode === 'submit') await execute(tasks[0]);
  else if (mode === 'continue') await execute(tasks[2]);
  else if (mode === 'status') await execute(tasks[1]);
  else if (['history', 'history-failure'].includes(mode)) await history();
  else { await page.screenshot({ path: path.join(output, 'inspect.png'), fullPage: true }); console.log(await page.locator('body').innerText()); }
}
main().catch(async error => {
  if (page) {
    console.error((await page.locator('body').innerText()).slice(0, 1800));
    const passwordVisible = await page.locator('input[type=password]:visible').count();
    if (!passwordVisible) await page.screenshot({ path: path.join(output, mode + '-failure.png'), fullPage: true });
  }
  console.error(JSON.stringify({ action: mode, error: error.message })); process.exitCode = 1;
}).finally(async () => { if (browser) await browser.close(); });
