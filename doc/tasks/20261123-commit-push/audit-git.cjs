const fs = require('node:fs');
const cp = require('node:child_process');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '../../..');
const git = (...args) => {
  const result = cp.spawnSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, windowsHide: true });
  if (result.status !== 0) throw new Error(`git ${args[0]} failed (${result.status})`);
  return result.stdout;
};
const rows = git('status', '--porcelain=v1', '-z', '-uall').split('\0').filter(Boolean);
const untracked = rows.filter(row => row.startsWith('?? ')).map(row => row.slice(3));
const counts = {};
for (const file of untracked) {
  const key = path.extname(file) || '(none)';
  counts[key] = (counts[key] || 0) + 1;
}
const upstream = git('rev-parse', '--abbrev-ref', '@{u}').trim();
const range = `${upstream}..HEAD`;
const objects = git('rev-list', '--objects', range);
const batch = cp.spawnSync('git', ['cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)'], {
  cwd: root, encoding: 'utf8', input: objects, maxBuffer: 64 * 1024 * 1024, windowsHide: true
});
if (batch.status !== 0) throw new Error('object size scan failed');
const blobs = batch.stdout.trim().split('\n').filter(Boolean).map(line => {
  const match = line.match(/^(\S+) (\S+) (\d+)(?: (.*))?$/);
  if (!match) throw new Error('invalid object metadata');
  return { oid: match[1], type: match[2], bytes: Number(match[3]), file: match[4] || '' };
}).filter(item => item.type === 'blob');
const patterns = [
  ['private-key', /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/],
  ['github-token', /\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b/],
  ['openai-token', /\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}/],
  ['aws-access-key', /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/],
  ['url-credential', /https?:\/\/[^\s/@:]+:[^\s/@]+@/],
];
const secretHits = [];
for (const blob of blobs) {
  if (blob.bytes > 10 * 1024 * 1024) continue;
  const body = git('cat-file', 'blob', blob.oid);
  if (body.includes('\0')) continue;
  const lines = body.split('\n');
  for (let index = 0; index < lines.length; index++) {
    for (const [rule, pattern] of patterns) {
      if (pattern.test(lines[index])) secretHits.push({ oid: blob.oid, file: blob.file, line: index + 1, rule });
    }
  }
}
let remote = git('remote', 'get-url', '--push', 'origin').trim();
remote = remote.replace(/(https?:\/\/)[^/@]+@/g, '$1[REDACTED]@').replace(/[?#].*$/, '');
const result = {
  branch: git('branch', '--show-current').trim(),
  head: git('rev-parse', 'HEAD').trim(), upstream, remote,
  aheadBehind: git('rev-list', '--left-right', '--count', `HEAD...${upstream}`).trim(),
  staged: git('diff', '--cached', '--name-status').trim().split('\n').filter(Boolean),
  commits: git('log', '--format=%h %s', range).trim().split('\n').filter(Boolean),
  committedPaths: git('diff', '--name-status', upstream, 'HEAD').trim().split('\n').filter(Boolean),
  actualUnstaged: git('-c', 'core.safecrlf=false', 'diff', '--numstat').trim().split('\n').filter(Boolean),
  untrackedCount: untracked.length, untrackedExtensions: counts,
  untrackedOutsideTasks: untracked.filter(file => !file.startsWith('doc/tasks/')),
  blobCount: blobs.length,
  largestBlobs: [...blobs].sort((a, b) => b.bytes - a.bytes).slice(0, 5),
  oversizedBlobs: blobs.filter(blob => blob.bytes > 100 * 1024 * 1024), secretHits,
  excludedPriorChangesDigest: crypto.createHash('sha256').update(JSON.stringify(rows.filter(row => !row.includes('20261123-commit-push/')))).digest('hex')
};
fs.writeFileSync(path.join(__dirname, 'initial-audit.json'), JSON.stringify(result, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(result, null, 2));
