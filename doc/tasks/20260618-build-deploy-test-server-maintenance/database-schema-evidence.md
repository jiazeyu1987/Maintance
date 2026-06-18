# Database Schema Evidence

## Data

- Target database: test server MySQL container `intruoyi-mysql`, schema `ruoyi-vue-pro`.
- Data path: no business data restore, no full database sync, no mock data.

## Migration

- Required migrations were executed through deploy-release, not by manual table creation.
- Same-package dependency order: `20260606_showroom_hall_product_canvas_layout` before `20260613_showroom_award_and_hall_item_schema`.

## Safety

- No fallback or downgrade path was introduced.
- Schema checks fail fast before application startup if required showroom tables or indexes are missing.

## Rollback

- No rollback was executed.
- Future rollback requires explicit user authorization through the release workflow.

## BDD:

- Given a release contains showroom award code and schema SQL, When deploy-release runs on test, Then required tables, columns, indexes, and migration states are present before backend/frontend are considered healthy.

## RED:

- Preflight planner originally blocked `20260613_showroom_award_and_hall_item_schema` because `20260606_showroom_hall_product_canvas_layout` was not yet `APPLIED` in target state.

## GREEN:

- `20260606_showroom_hall_product_canvas_layout`, `20260613_showroom_award_and_hall_item_schema`, and `20260618_showroom_publicity_role_menu_scope` are `APPLIED` on test.
- Remote schema query confirms required columns, tables, and indexes.

## Verification

- Remote MySQL query over SSH passed.
- Deploy script `Assert-RemoteShowroomAwardSchemaReady` passed before backend/frontend startup.

## Blockers

- Resolved: stale release lock from previous failed deployment.
- Resolved: preflight planner dependency handling for migrations applied earlier in the same plan.

## Scope

- Target environment: `test`
- Target host: `172.30.30.58`
- Release tag: `release-20260618-1742-showroom-sql-vite`
- Schema area: showroom award and mixed hall item schema.

## Migration State

- `20260606_showroom_hall_product_canvas_layout` -> `APPLIED`
- `20260613_showroom_award_and_hall_item_schema` -> `APPLIED`
- `20260618_showroom_publicity_role_menu_scope` -> `APPLIED`
- Release operation lock for `test` -> `APPLIED`

## Tables And Columns

- `showroom_hall_product.layout_x` exists, `decimal(8,6)`, nullable.
- `showroom_hall_product.layout_y` exists, `decimal(8,6)`, nullable.
- `showroom_hall_product.layout_width` exists, `decimal(8,6)`, nullable.
- `showroom_hall_product.layout_height` exists, `decimal(8,6)`, nullable.
- `showroom_award` exists.
- `showroom_award_revision` exists.
- `showroom_hall_item` exists.

## Indexes

- `showroom_award.uk_showroom_award_code` -> `tenant_id,award_code`
- `showroom_award_revision.uk_showroom_award_revision_no` -> `tenant_id,award_id,revision_no`
- `showroom_award_revision.idx_showroom_award_revision_award` -> `tenant_id,award_id,status`
- `showroom_hall_item.uk_showroom_hall_item` -> `tenant_id,hall_id,item_type,item_id`
- `showroom_hall_item.idx_showroom_hall_item_order` -> `tenant_id,hall_id,display_order,id`
- `showroom_hall_item.idx_showroom_hall_item_item` -> `tenant_id,item_type,item_id`

## Verification

- GREEN: remote schema query over SSH and MySQL -> PASS.
- GREEN: deploy script `Assert-RemoteShowroomAwardSchemaReady` -> PASS before backend/frontend startup.
- No fallback, no manual table creation, no backup restore path used.
