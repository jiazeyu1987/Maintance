const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const source = fs.readFileSync(`${__dirname}/intruoyi_login.py`, 'utf8');
const script = source.match(/_SCRIPT = r'''([\s\S]*?)'''/)[1];

async function run(saved = 'DEVELOPMENT_DISABLED', runtime = {mode: saved, auditEnabled: false}, status = 200, code = 0) {
  const reads = [];
  const chain = {waitFor: async () => {}, fill: async () => {}, click: async () => {}};
  const auth = {status: () => 200, request: () => ({postDataJSON: () => ({username: 'user'}), headers: () => ({'tenant-id': '1'})}),
    json: async () => ({code: 0, data: {userId: 1, accessToken: 'private-token'}})};
  const page = {
    goto: async () => {}, getByRole: () => chain, getByPlaceholder: () => chain, locator: () => chain,
    waitForResponse: async () => auth, waitForURL: async () => {}, screenshot: async () => {},
    url: () => 'http://target/user/profile',
    request: {get: async (url, options) => {
      reads.push(url);
      assert.equal(options.headers.Authorization, 'Bearer private-token');
      assert.equal(options.headers['tenant-id'], '1');
      assert.equal(options.maxRedirects, 0);
      assert.ok(url.startsWith('http://target/admin-api/'));
      return {status: () => status, json: async () => ({code, data: url.includes('get-value-by-key') ? saved : runtime})};
    }}
  };
  const input = {target: 'http://target', credentials: {username: 'user', password: 'private-password', tenantName: 'test'}, readGxpMode: true, screenshot: 'unused.png'};
  const result = await eval(`(${script.replace('__INPUT__', JSON.stringify(input))})`)(page);
  assert.equal(reads.length, 2);
  assert.ok(reads.some(url => url.includes('/infra/config/get-value-by-key?key=system.gxp.audit-mode')));
  assert.ok(reads.every(url => !url.includes('/config/page')));
  assert.ok(!JSON.stringify(result).includes('private-'));
  return result;
}
test('platform saved mode works without a tenant config row', async () => {
  const result = await run();
  assert.equal(result.gxpAuditMode, 'DEVELOPMENT_DISABLED');
  assert.equal(result.pendingRestart, false);
});
test('formal mode requires enabled runtime auditing', async () => {
  assert.equal((await run('FORMAL', {mode: 'FORMAL', auditEnabled: true})).auditEnabled, true);
});
for (const mode of [null, '', 'LOCAL_POLICY', 'unknown']) {
  test(`reject missing or unsupported saved mode ${mode}`, async () => { await assert.rejects(run(mode)); });
}
test('reject saved/runtime mismatch', async () => { await assert.rejects(run('DEVELOPMENT_DISABLED', {mode: 'FORMAL', auditEnabled: true})); });
test('reject incorrect runtime auditing flag', async () => { await assert.rejects(run('FORMAL', {mode: 'FORMAL', auditEnabled: false})); });
test('reject HTTP failures and application errors', async () => {
  await assert.rejects(run('DEVELOPMENT_DISABLED', {}, 403));
  await assert.rejects(run('DEVELOPMENT_DISABLED', {}, 200, 500));
});
