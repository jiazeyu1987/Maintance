// Real UI automation. Secrets never appear in CLI arguments, snapshots or traces.
import { createRequire } from 'node:module';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
const require = createRequire('E:/IntRuoyi/IntRuoyiFronted/package.json');
const { chromium } = require('playwright');
const privateDir = 'E:/Int/CacheData/IntRuoyi/spug-integration-20261010';
const admin = JSON.parse(await readFile(privateDir + '/admin.private.json', 'utf8'));
const backend = JSON.parse(await readFile(privateDir + '/backend.private.json', 'utf8'));
if (backend.publishEnabled !== false || backend.productionPaused !== true) {
  throw new Error('Code-only UI verification requires publishEnabled=false and productionPaused=true.');
}
const output = 'doc/tasks/20261010-spug-integration';
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.setDefaultTimeout(10000);
try {
  await page.goto('http://127.0.0.1:18080', { waitUntil: 'domcontentloaded' });
  await page.getByPlaceholder('请输入账户').fill(admin.username);
  await page.getByPlaceholder('请输入密码').fill(admin.password);
  await page.getByRole('button', { name: '登 录' }).click();
  const warning = page.getByRole('button', { name: '知道了' });
  await warning.waitFor({ state: 'visible', timeout: 10000 });
  await warning.click();
  await warning.waitFor({ state: 'hidden' });
  await page.getByText('工作台', { exact: true }).first().waitFor();
  const action = process.argv[2] || 'inspect';
  const live = action.startsWith('schedule-live-');
  const onlyTargets = process.argv.find(v => v.startsWith('--targets='))?.slice(10).split(',');
  if (['new', 'command', 'host'].includes(action)) {
    await page.getByText('流水线', { exact: true }).first().click();
    await page.getByRole('button', { name: /新建/ }).waitFor();
  }
  if (['new', 'command', 'host'].includes(action)) {
    await page.getByRole('button', { name: /新建/ }).click();
  }
  if (['command', 'host'].includes(action)) {
    await page.getByText('执行命令', { exact: true }).click();
  }
  if (action === 'host') await page.getByText('添加目标主机', { exact: true }).click();
  if (action.startsWith('schedule')) {
    await page.getByText('任务计划', { exact: true }).first().click();
    await page.getByRole('button', { name: /新建/ }).waitFor();
  }
  if (action === 'schedule-new') await page.getByRole('button', { name: /新建/ }).click();
  const tasks = [
    { name: '发布状态查询', target: 'ALL', mode: 'status', expected: 'READ_ONLY_QUERY_COMPLETE' },
    { name: '发布测试服', target: 'TEST', mode: live ? 'check' : 'publish', expected: live ? 'MANUAL_TEST_CHECK_ONLY' : 'PUBLISH_HOLD' },
    { name: '发布备份服', target: 'BACKUP', mode: 'publish', expected: 'TARGET_PUBLISH_DISABLED' },
    { name: '发布正式服', target: 'PROD', mode: 'publish', expected: 'PRODUCTION_PAUSED' },
  ];
  if (action === 'schedule-install') {
    for (const task of tasks) {
      if (await page.getByRole('row').filter({ has: page.getByText(task.name, { exact: true }) }).count()) continue;
      await page.getByRole('button', { name: /新建/ }).click();
      let dialog = page.getByRole('dialog', { name: '新建任务' });
      await dialog.getByRole('button', { name: '添加类型' }).click();
      const typeDialog = page.locator('.ant-modal-confirm').filter({ hasText: '添加任务类型' });
      await typeDialog.locator('input').fill('IntRuoyi手动发布');
      await typeDialog.getByRole('button', { name: /确\s*定/ }).click();
      await dialog.getByPlaceholder('请输入任务名称').fill(task.name);
      await dialog.locator('.ace_content').click();
      await page.keyboard.press('Control+A');
      await page.keyboard.insertText('python3 /opt/intruoyi-spug/release_adapter.py --target ' + task.target +
        ' --mode ' + task.mode);
      await dialog.getByPlaceholder('请输入模板备注信息').fill(task.mode === 'status'
        ? '读取固定版本和原任务；查询成功不代表发布成功。'
        : '仅手动：更多→执行测试；不要激活定时任务。提交受理不代表完整验收；暂停时拒绝部署。');
      await dialog.getByRole('button', { name: '下一步', exact: true }).click();
      await dialog.getByRole('spinbutton').fill('3600');
      await dialog.getByRole('button', { name: '下一步', exact: true }).click();
      await dialog.getByRole('combobox').click();
      await page.getByText('本机', { exact: true }).last().click();
      await dialog.getByRole('button', { name: /提\s*交/ }).click();
      await dialog.waitFor({ state: 'hidden' });
      const row = page.getByRole('row').filter({ has: page.getByText(task.name, { exact: true }) });
      await row.getByText('未激活', { exact: true }).waitFor();
      console.log('Created through real UI; schedule inactive: ' + task.name);
    }
  }
  if (['schedule-update', 'schedule-live-configure'].includes(action)) {
    for (const task of tasks.filter(t => !onlyTargets || onlyTargets.includes(t.target))) {
      const row = page.getByRole('row').filter({ has: page.getByText(task.name, { exact: true }) });
      await row.getByText('未激活', { exact: true }).waitFor();
      await row.getByText('编辑', { exact: true }).click();
      const dialog = page.getByRole('dialog', { name: '编辑任务' });
      await dialog.locator('.ace_content').click();
      await page.keyboard.press('Control+A');
      await page.keyboard.insertText('python3 /opt/intruoyi-spug/release_adapter.py --target ' + task.target + ' --mode ' + task.mode);
      await dialog.getByPlaceholder('请输入模板备注信息').fill(task.mode === 'status'
        ? '只读查询固定包与原操作；区分部署成功和完整验收失败。更多→执行测试；历史记录查看结果。禁止激活。'
        : task.mode === 'check'
        ? '手动 TEST 入口：更多→执行测试。默认只读查询明确版本及原操作，区分部署和完整验收；已有包批准只约束接纳动作。不部署、不重建。禁止激活。'
        : '当前目标发布关闭；更多→执行测试只显示拒绝原因。正式维护暂停。禁止激活。');
      await dialog.getByRole('button', { name: '下一步', exact: true }).click();
      await dialog.getByRole('button', { name: '下一步', exact: true }).click();
      await dialog.getByRole('button', { name: /提\s*交/ }).click();
      await dialog.waitFor({ state: 'hidden' });
      await row.getByText('未激活', { exact: true }).waitFor();
      console.log('Updated own existing inactive task through UI: ' + task.name);
    }
  }
  if (['schedule-code-only-test', 'schedule-status-only', 'schedule-live-test'].includes(action)) {
    const evidenceName = live ? 'live-real-ui-20261012.json' : action === 'schedule-status-only' ? 'real-ui-status-restored-20261011.json' : 'real-ui-code-only-20261011.json';
    const results = live && onlyTargets ? JSON.parse(await readFile(output + '/' + evidenceName, 'utf8'))
      .filter(t => !tasks.some(v => v.name === t.name && onlyTargets.includes(v.target))) : [];
    for (const task of (action === 'schedule-status-only' ? tasks.slice(0, 1) : tasks).filter(t => !onlyTargets || onlyTargets.includes(t.target))) {
      const startedAt = new Date().toISOString();
      const row = page.getByRole('row').filter({ has: page.getByText(task.name, { exact: true }) });
      await row.getByText('未激活', { exact: true }).waitFor();
      await row.getByText('更多', { exact: true }).click();
      await page.getByText('执行测试', { exact: true }).last().click();
      const accepted = page.waitForResponse(r => r.url().includes('/api/schedule/') && r.request().method() === 'POST', { timeout: 65000 });
      await page.locator('.ant-modal-confirm').filter({ hasText: '操作确认' }).getByRole('button', { name: /确\s*定/ }).click();
      const execution = await (await accepted).json();
      const info = page.getByRole('dialog', { name: '任务执行详情' });
      if (task.mode === 'publish') {
        await info.getByText(task.expected, { exact: false }).waitFor({ timeout: 60000 });
      } else {
        await info.getByText(/READ_ONLY_QUERY_COMPLETE|BACKEND_UNAVAILABLE|BACKEND_HTTP_REFUSED|BACKEND_REFUSED/, { exact: false }).waitFor({ timeout: 60000 });
      }
      const detail = await info.innerText();
      const unavailable = /BACKEND_UNAVAILABLE|BACKEND_HTTP_REFUSED|BACKEND_REFUSED/.test(detail);
      const expectedExit = task.mode === 'status' && !unavailable ? 0 : 2;
      const actualExpectedExit = task.mode === 'check' && !unavailable ? 0 : expectedExit;
      if (!detail.includes('返回状态： ' + actualExpectedExit)) throw new Error('Unexpected real execution exit: ' + task.name);
      if (task.mode === 'publish' && !detail.includes('"outcome": "REFUSED_OR_UNAVAILABLE"')) {
        throw new Error('Closed publish entry did not return its explicit refusal');
      }
      if (live && ['status', 'check'].includes(task.mode)) {
        for (const text of ['部署：已成功', 'EXISTING_BACKEND_RECORD', 'bf37637e-1059-4255-be00-36bc46818cde']) {
          if (!detail.includes(text)) throw new Error('Actual original deployment mapping missing: ' + text);
        }
        if (!detail.includes('DEPLOYED_ACCEPTANCE_FAILED') && !detail.includes('DEPLOYED_ACCEPTANCE_UNAVAILABLE')) {
          throw new Error('Deployment and acceptance were not separately mapped');
        }
        const lines = detail.split('\n').filter(line => line.startsWith('{'));
        if (task.mode === 'check') {
          const check = lines.map(line => JSON.parse(line)).find(value => value.outcome === 'MANUAL_TEST_CHECK_ONLY');
          if (!check || check.deploymentSubmitted !== false || check.publishEnabled !== false) {
            throw new Error('Manual TEST entry did not remain read-only');
          }
          if (check.admissionStatus === 'NOT_CONFIGURED_IN_NORMAL_BUILD_MODE' && check.existingPackageApprovalVerified !== false) {
            throw new Error('Normal build mode falsely accepted old package approval');
          }
        }
        for (const line of lines) {
          const value = JSON.parse(line);
          if (value.requests?.some(r => r.method !== 'GET' && r.path !== '/system/auth/login')) {
            throw new Error('Read-only UI task issued a release write');
          }
        }
      }
      await page.screenshot({ path: output + '/' + action + '-' + (live ? '20261012' : '20261011') + '-' + task.target + '-' + task.mode + '.png', fullPage: true });
      results.push({ name: task.name, startedAt, completedAt: new Date().toISOString(), expectedExit: actualExpectedExit,
                     historyId: execution.data, releasePostIssued: false, acceptanceQueryAvailable: !unavailable,
                     result: unavailable ? '待联调：真实后端不可达或拒绝历史绑定查询' : task.mode === 'status' ? '只读查询完成' : '实际开关拒绝，无部署提交', detail });
      await writeFile(output + '/' + evidenceName, JSON.stringify(results, null, 2), 'utf8');
      await info.getByRole('button', { name: 'Close', exact: true }).click();
      console.log('Real UI path: ' + task.name + ' / exit=' + actualExpectedExit);
    }
    await writeFile(output + '/' + evidenceName, JSON.stringify(results, null, 2), 'utf8');
  }
  if (action === 'schedule-live-history') {
    const expected = JSON.parse(await readFile(output + '/live-real-ui-20261012.json', 'utf8'));
    const persistencePath = output + '/live-real-ui-persistence-20261012.json';
    const results = onlyTargets ? JSON.parse(await readFile(persistencePath, 'utf8'))
      .filter(t => !tasks.some(v => v.name === t.name && onlyTargets.includes(v.target))) : [];
    for (const task of tasks.filter(t => !onlyTargets || onlyTargets.includes(t.target))) {
      const row = page.getByRole('row').filter({ has: page.getByText(task.name, { exact: true }) });
      await row.getByText('未激活', { exact: true }).waitFor();
      await row.getByText('更多', { exact: true }).click();
      const listing = page.waitForResponse(r => r.url().includes('/api/schedule/') && r.request().method() === 'GET' && !r.url().includes('?'));
      await page.getByText('历史记录', { exact: true }).last().click();
      const records = (await (await listing).json()).data;
      const history = page.getByRole('dialog', { name: '任务执行记录 - ' + task.name });
      await history.getByText('详情', { exact: true }).first().waitFor();
      const previous = expected.find(t => t.name === task.name) || { historyId: records[0].id };
      if (records[0].id !== previous.historyId) throw new Error('Original historical UI record changed');
      const response = page.waitForResponse(r => r.url().includes('/api/schedule/') && r.url().endsWith('?id=' + previous.historyId));
      await history.getByText('详情', { exact: true }).first().click();
      await response;
      const info = page.getByRole('dialog', { name: '任务执行详情' });
      await info.getByText(task.mode === 'publish' ? task.expected : /DEPLOYED_ACCEPTANCE_FAILED|DEPLOYED_ACCEPTANCE_UNAVAILABLE/, { exact: false }).waitFor();
      const detail = await info.innerText();
      if (task.mode !== 'publish' && (!detail.includes('部署：已成功') ||
          !detail.includes('bf37637e-1059-4255-be00-36bc46818cde'))) throw new Error('Persisted original mapping missing');
      await info.screenshot({ path: output + '/live-history-20261012-' + task.target + '.png', animations: 'disabled' });
      results.push({ name: task.name, historyId: previous.historyId, detail, readAfterFreshLogin: true,
                     deploymentSubmitted: false, observedAt: new Date().toISOString() });
      await info.getByRole('button', { name: 'Close', exact: true }).click();
      await history.getByRole('button', { name: 'Close', exact: true }).click();
    }
    await writeFile(persistencePath, JSON.stringify(results, null, 2), 'utf8');
    console.log('Fresh-login original Spug history verified; no command re-execution.');
  }
  await mkdir(output, { recursive: true });
  await page.screenshot({ path: output + '/spug-' + action + '.png', fullPage: true });
  const text = await page.locator('body').innerText();
  await writeFile(output + '/spug-' + action + '-ui.txt', text, 'utf8');
  console.log(text.slice(0, 5000));
  console.log(JSON.stringify(await page.locator('input,textarea').evaluateAll(nodes => nodes.map(n => ({
    tag: n.tagName, placeholder: n.getAttribute('placeholder'), id: n.id, type: n.getAttribute('type')
  })))));
  console.log('UI result: real administrator login accepted; URL=' + page.url());
} catch (error) {
  await page.screenshot({ path: output + '/spug-ui-failure.png', fullPage: true });
  console.log((await page.locator('body').innerText()).slice(0, 3500));
  throw error;
} finally {
  await browser.close();
}
