const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function load(search) {
  const classes = [], bases = [];
  const document = {
    documentElement: {classList: {add: name => classes.push(name)}},
    head: {append: node => bases.push(node)},
    createElement: tag => ({tagName: tag}),
  };
  const file = path.join(__dirname, 'embedded.js');
  if (fs.existsSync(file)) vm.runInNewContext(fs.readFileSync(file, 'utf8'), {document, window: {location: {search}}, URLSearchParams});
  return {classes, bases};
}

test('explicit embedded mode reuses the page and sends login navigation to Spug shell', () => {
  const page = load('?embedded=1');
  assert.deepEqual(page.classes, ['spug-embedded']);
  assert.equal(page.bases[0].tagName, 'base');
  assert.equal(page.bases[0].target, '_top');
  assert.equal(page.bases[0].href, undefined);
});

test('standalone page keeps original layout and navigation', () => {
  for (const search of ['', '?embedded=0', '?other=1']) assert.deepEqual(load(search), {classes: [], bases: []});
});
