const cp = require('child_process');

const releaseTag = 'release-20260820-frozen-head-test-r260820a-r2';

const script = String.raw`
set -euo pipefail
tag="$1"

sql() {
  docker exec -i intruoyi-mysql sh -lc 'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro' <<SQL
$1
SQL
}

lock_columns=$(sql "SHOW COLUMNS FROM infra_release_operation_lock;")
migration_columns=$(sql "SHOW COLUMNS FROM infra_release_migration;")
running_locks=$(sql "SELECT COUNT(*) FROM infra_release_operation_lock WHERE status='RUNNING';")
latest_locks=$(sql "SELECT * FROM infra_release_operation_lock LIMIT 5;" | base64 -w0)
target_migrations=$(sql "SELECT status, COUNT(*) FROM infra_release_migration WHERE release_tag='$tag' GROUP BY status;" | base64 -w0)
target_failed_running=$(sql "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag='$tag' AND status IN ('FAILED','RUNNING');")
all_failed_running=$(sql "SELECT release_tag, status, COUNT(*) FROM infra_release_migration WHERE status IN ('FAILED','RUNNING') GROUP BY release_tag, status ORDER BY release_tag, status;" | base64 -w0)

printf '{\n'
printf '  "releaseTag": "%s",\n' "$tag"
printf '  "runningLocks": %s,\n' "$running_locks"
printf '  "targetFailedRunning": %s,\n' "$target_failed_running"
printf '  "lockColumnsBase64": "%s",\n' "$(printf '%s' "$lock_columns" | base64 -w0)"
printf '  "migrationColumnsBase64": "%s",\n' "$(printf '%s' "$migration_columns" | base64 -w0)"
printf '  "latestLocksBase64": "%s",\n' "$latest_locks"
printf '  "targetMigrationsBase64": "%s",\n' "$target_migrations"
printf '  "allFailedRunningBase64": "%s"\n' "$all_failed_running"
printf '}\n'
`;

const result = cp.spawnSync('ssh', ['root@172.30.30.58', 'bash', '-s', '--', releaseTag], {
  input: script,
  encoding: 'utf8',
  maxBuffer: 20 * 1024 * 1024,
});

if (result.stderr) {
  process.stderr.write(result.stderr);
}
if (result.stdout) {
  process.stdout.write(result.stdout);
}
process.exit(result.status ?? 1);
