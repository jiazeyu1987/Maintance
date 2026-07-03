# Manifest validation failure evidence

- capturedAt: 2026-07-03 23:51:34 +08:00
- releaseTag: `release-20260703-2335-codeonly-three-env`
- manifestPath: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260703-2335-codeonly-three-env\release-manifest.json`
- failure: manifest lacks required `sourceRepos`; cannot prove backend/frontend/maintenance branch, commit, and dirty=false from manifest.
- impact: this releaseTag is rejected for the requested three-environment closure and must not be published further.
- current allowed next step: fix manifest source repo generation/check, commit the fix, rebuild a new releaseTag, then restart the closure from build-release.
