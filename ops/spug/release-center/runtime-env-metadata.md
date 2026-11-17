# Runtime IMAGE_TAG alignment

Spug replaces containers using immutable image digests. Legacy compose `.env`
metadata must also match the completed release before operational closeout.

Run `runtime_env_metadata.py` from an isolated maintenance worktree after the
selected target's deployment, version, upgrade and real login checks pass. Supply
the private executor configuration, explicit environment/release, the previously
observed IMAGE_TAG and the confirmed runtime `.env` path. The default is read-only
verification; `--apply` performs alignment. Configuration values are never printed.

The command binds the registered package and manifest digest, takes the same remote
runtime operation lock as Spug, checks both running image digests and tags, then
compares the existing IMAGE_TAG. It preserves every other byte and the original
file ownership/mode, stores a private 0600 original under the registered staging
directory, replaces the single line atomically and reads it back. It does not
restart the application, change migration records or replace business acceptance.

A wrong/missing/duplicate IMAGE_TAG, changed image, active task, unknown lock or
missing technical proof blocks the command. Inspect the original evidence after a
disconnect; do not repeat a write with stale expectations. Failed alignment means
release closeout is incomplete even if the application remains healthy.

Example (paths and old tag must come from the current configuration/observation):

```powershell
python -X utf8 ops/spug/release-center/runtime_env_metadata.py --config <private-config> --environment prod --release-tag <verified-tag> --expected-current-tag <observed-tag> --env-file <confirmed-env-file>
```

Validation: `python -X utf8 scripts/tests/test_runtime_env_metadata.py`.
