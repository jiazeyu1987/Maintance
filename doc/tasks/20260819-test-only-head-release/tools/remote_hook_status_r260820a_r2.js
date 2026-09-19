const cp = require('child_process');

const script = String.raw`
set -euo pipefail
cid=$(docker ps --filter name=intruoyi-runtime-backend-run --format '{{.ID}}' | head -n 1)
printf 'CID=%s\n' "$cid"
if [ -n "$cid" ]; then
  docker inspect "$cid" --format 'status={{.State.Status}} running={{.State.Running}} started={{.State.StartedAt}} image={{.Config.Image}}'
  docker logs --tail 80 "$cid" 2>&1 | sed -E 's/-p[^[:space:]]+/-p<redacted>/g'
fi
`;

const result = cp.spawnSync('ssh', ['root@172.30.30.58', 'bash', '-s'], {
  input: script,
  encoding: 'utf8',
  maxBuffer: 10 * 1024 * 1024,
});

if (result.stderr) process.stderr.write(result.stderr);
if (result.stdout) process.stdout.write(result.stdout);
process.exit(result.status ?? 1);
