'use strict';
// Rendering-only checks: these fixtures do not execute or verify a recovery.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'smallapp-ui', 'app.js'), 'utf8');
const states = source.match(/^const states = .*;$/m)[0];
const showResult = source.slice(source.indexOf('function showResult(record){'), source.indexOf('\nfunction history(){'));

function display(action, state) {
  const elements = new Map();
  const document = {getElementById(id) {
    if (!elements.has(id)) elements.set(id, {textContent: '', hidden: true, replaceChildren() {}});
    return elements.get(id);
  }};
  const context = vm.createContext({document});
  vm.runInContext('const $ = id => document.getElementById(id);\n' + states + '\n' + showResult, context);
  const record = {request: {action}, result: state === null ? null : {
    state, errorCode: null, logRefs: ['original-log'], resultRef: 'original-result',
  }};
  context.record = record;
  vm.runInContext('showResult(record)', context);
  return id => elements.get(id);
}

test('RESTORE success reports recovery and protected startup while business acceptance remains pending', () => {
  // The frozen result has no business-acceptance field; a successful operation
  // must not be presented as successful login, records or attachment acceptance.
  const element = display('RESTORE', 'SUCCEEDED');
  assert.equal(element('result-state').textContent, '数据恢复及保护启动完成，业务验收尚未完成。');
  assert.equal(element('result-details').hidden, false);
  assert.equal(element('result-logs').textContent, 'original-log');
  assert.equal(element('result-ref').textContent, 'original-result');
});

for (const action of ['FULL', 'INCREMENTAL']) {
  test(action + ' success retains the backup result wording', () => {
    assert.equal(display(action, 'SUCCEEDED')('result-state').textContent, '执行完成');
  });
}

for (const [state, expected] of [
  ['RUNNING', '原操作执行或核对中'],
  ['FAILED', '原操作失败'],
  [null, '已保留编号，尚未查询执行回执'],
]) {
  test('RESTORE ' + state + ' does not claim completed recovery', () => {
    assert.equal(display('RESTORE', state)('result-state').textContent, expected);
  });
}
