# Frontend Feature Evidence

## Scope

- `frontend/src/App.vue`
- `scripts/verify_contracts.py`

## Contract

Frontend runtime-control action payload must match the original Vue page: only submit fields supported by the selected action.

## Evidence

- `scripts/verify_contracts.py` 增加前端 payload 原版契约检查：按动作调用 `operationSupportsPublishScope`、`operationUsesReleaseTag`、`operationRequiresTargetEnvironment`、`operationUsesTestConclusion`，并禁止无条件提交构建字段和硬编码测试结论。
- `python -X utf8 scripts\verify_contracts.py` -> PASS。
- `pnpm --dir frontend typecheck` -> PASS。
- `pnpm --dir frontend build` -> PASS，Vite 构建成功，存在 chunk size warning。
