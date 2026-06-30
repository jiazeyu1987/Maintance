# 20260629 将 Intruoyi 已提交 git 版本发布到测试服务器执行日志

GREEN: experience-preflight-20260629-build-publish-test-committed-head -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`。已确认本轮只允许执行 `build-release -> publish-test -> 测试服运行态验证`，不推进 `mark-tested`、正式服或备份服。

GREEN: committed-head-gap-check-20260629 -> PASS，已核对当前三仓 HEAD 与测试服当前运行版本差异：
- 维护仓当前 HEAD=`4fa706d41210434b0c97eab699a0c4756b29d8cc`，测试服当前成功发布链路使用的维护提交同为 `4fa706d41210434b0c97eab699a0c4756b29d8cc`
- 后端仓当前 HEAD=`c1302d1f85f8ff940c9b3fe1fb45e92a8464bb17`
- 前端仓当前 HEAD=`705fc215415dec0f5608820c88f8aecf5d7c45fd`
- 测试服当前运行 releaseTag=`release-20260629-1415-build-test-v3`
- 该 releaseTag 的 manifest 中后端提交=`c60d2c5b47d4931ff5bd120b167caf013a3f652b`、前端提交=`63cedb397d2caa4b394d4c5e7821c76652493d4b`
结论：测试服当前运行版本不是当前前后端仓库的已提交 HEAD，不能直接判定本轮目标已完成，必须重新走真实发布链路。

GREEN: dirty-workspace-release-isolation-check-20260629 -> PASS，已核对主工作区未提交状态：
- 维护仓 `git status --short` 共 `55` 项
- 后端仓 `git status --short` 共 `105` 项
- 前端仓 `git status --short` 共 `45` 项
结论：主工作区存在大量未提交脏改，本轮若要发布“已提交 git 版本”，必须使用干净 worktree 隔离各仓库 HEAD；禁止直接从当前主工作区构建发布包。

GREEN: committed-head-release-worktree-setup-20260629 -> PASS，已创建并切换本机发布输入到当前已提交 HEAD 的干净 worktree：
- 后端 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260629-c1302d1` -> `c1302d1f85f8ff940c9b3fe1fb45e92a8464bb17`
- 前端 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260629-705fc21` -> `705fc215415dec0f5608820c88f8aecf5d7c45fd`
- 维护控制台本地配置 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260629-4fa706d\config\runtime-control.local.yaml` 已改为指向上述两套新 worktree
- 本机 runtime-control 已重启，`http://127.0.0.1:48181/actuator/health` 返回 `{"status":"UP"}`
- `build-release` 预览命令已确认 `-BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260629-c1302d1` 与 `-FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260629-705fc21`

BLOCKER: committed-head-frontend-lockfile-policy-20260629 -> 当前前端“已提交 HEAD”本身不可发布。对干净前端 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260629-705fc21` 执行 `pnpm install --frozen-lockfile` 时，供应链锁文件门禁报 `ERR_PNPM_TARBALL_URL_MISMATCH`，明确指出 5 个 lockfile 条目仍为 `registry.npmmirror.com`：
- `cross-env@7.0.3`
- `dayjs-plugin-lunar@1.4.1`
- `dhtmlx-gantt@9.1.1`
- `jsbarcode@3.12.3`
- `tyme4ts@1.4.6`
而主前端工作区 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\pnpm-lock.yaml` 存在未提交修复，已把这 5 个 tarball URL 改为 `https://registry.npmjs.org/...`。结论：当前 git 已提交前端 HEAD `705fc215415dec0f5608820c88f8aecf5d7c45fd` 仍未包含必要锁文件修复，无法在不混入未提交改动的前提下继续 `build-release`。

GREEN: committed-head-frontend-release-prereq-fix-20260629 -> PASS，已在前端仓将发布前置修复正式提交进 git：
- commit `21a09c9b3c4864aa1c480d2f1f379994c32ea059`：修复 `pnpm-lock.yaml` 中 5 个 tarball URL 的供应链门禁冲突
- commit `1ffcdca22b735df762a581b2eed207a4581e8a71`：补齐 `pnpm-workspace.yaml` 中 `allowBuilds` 放行配置，覆盖 `@parcel/watcher`、`@swc/core`、`core-js`、`core-js-pure`、`es5-ext`、`esbuild` 与 `vue-demi`
随后已重建新的干净前端发布 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260629-1ffcdca`，对应 HEAD=`1ffcdca22b735df762a581b2eed207a4581e8a71`；维护控制台本地配置也已切换为指向该新前端 worktree。当前“已提交 git 版本”的前端发布前置已满足，可继续真实 `build-release`。

RED: committed-head-build-release-20260629-v1 -> FAIL，真实 `build-release` operation `op-2026-06-29T091456891419800Z-940615fa-3169-4858-8b56-b750357e1f64` 最终状态 `FAILED`，releaseTag=`release-20260629-1705-committed-head-v1`。日志确认本轮构建命令已正确指向：
- 后端 `D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260629-c1302d1`
- 前端 `D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260629-1ffcdca`
且已越过前端供应链与 build scripts 门禁；真实失败点发生在 migration policy gate，明确报错：`dependsOn missing migration '20260629_menu_title_srm_dcc_rename' for migrationId '20260629_srm_admin_role_visibility'`。当前新的唯一 blocker 为后端 SQL 发布契约缺失，需先修复该 migration 依赖声明，再继续新的真实 `build-release`。

GREEN: committed-head-backend-root-cause-recheck-20260629 -> PASS，继续只读核对后端主仓、旧发布 worktree 与 migration 文件归属：
- 后端主仓当前 HEAD=`e4d82d1703f8238f283a91a7a4f81cdddbb90755`
- 旧后端发布 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260629-c1302d1` 的 HEAD=`c1302d1f85f8ff940c9b3fe1fb45e92a8464bb17`
- `git log --oneline -- sql/mysql/20260629_menu_title_srm_dcc_rename.sql` 显示该 SQL 已在当前后端已提交 HEAD 中
- `runtime-control.local.yaml` 当前 `repo-root` 仍指向旧后端发布 worktree `...c1302d1`
结论：`committed-head-build-release-20260629-v1` 的真实根因不是 migration 文件仍未提交，而是本轮 runtime-control 后端发布输入还停留在旧已提交 HEAD，导致新的 migration 文件没有进入实际 `build-release` 输入。下一步必须重建并切换到后端最新已提交 HEAD 对应的干净 worktree，然后重新执行真实 `build-release`。

RED: committed-head-build-release-20260629-v2 -> FAIL，切换后端发布输入到 `e4d82d1703f8238f283a91a7a4f81cdddbb90755` 后重新执行真实 `build-release`，operation=`op-2026-06-29T092655969557Z-4db8951d-758f-418c-856e-c862a3ce63cf`，releaseTag=`release-20260629-1730-committed-head-v2`。新的真实失败点不再是 migration gate，而是后端 `yudao-spring-boot-starter-security` 模块 `testCompile` 缺少 `org.junit.jupiter.api` / `org.mockito` 测试依赖；确认当前干净 release worktree 不包含主工作区 `pom.xml` 的未提交测试依赖修复，因此本轮“已提交 HEAD”自身仍不可构建。

GREEN: committed-head-backend-test-deps-release-fix-20260629 -> PASS，已在后端仓以独立任务 `20260629-security-starter-test-deps-release-fix` 最小提交测试依赖修复，commit=`7e2fa923c86a7a3db2eabcdbe34288e7cf77e27c`，仅补齐 `yudao-spring-boot-starter-security/pom.xml` 的 `spring-boot-starter-test` 与 `mockito-inline` test scope 依赖。定向验证 `mvn -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-framework/yudao-spring-boot-starter-security -DskipTests test -q` -> PASS。

GREEN: committed-head-build-release-20260629-v3 -> PASS，维护控制台切换到后端干净 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260629-7e2fa92` 与前端干净 worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260629-1ffcdca` 后，真实 `build-release` operation=`op-2026-06-29T093521215077Z-ee2add7b-9660-474b-a464-55a2d8192828` 最终 `SUCCESS`，releaseTag=`release-20260629-1745-committed-head-v3`。manifest 已核对：
- 后端 commit=`7e2fa923c86a7a3db2eabcdbe34288e7cf77e27c`
- 前端 commit=`1ffcdca22b735df762a581b2eed207a4581e8a71`
- 两者 `dirty=false`

RED: committed-head-publish-test-20260629-v3 -> FAIL，真实 `publish-test` operation=`op-2026-06-29T094854332306600Z-4d5b2a05-4674-4679-8309-84b1c36c58ce` 最终 `FAILED`。当前失败点不是发布包缺失、SSH、容器镜像、manifest 或 migration 记录写入，而是测试服执行 required SQL `20260618_srm_d7_1_code_rule_baseline.sql` 时，MySQL 抛出：
`ERROR 1644 (45000) at line 260: Missing SRM clean menu id range; conflicting system_menu rows exist`
结论：当前唯一 blocker 已收敛为测试服真实 `system_menu` 数据状态与该 required SQL 的 clean menu id range 契约冲突；在处理该数据库/SQL 契约前，不得继续判定测试服发布成功。
GREEN: committed-head-build-release-20260629-v6 -> PASS，真实 `build-release` operation=`op-2026-06-29T111441016266300Z-e5e96359-e505-40dc-9390-62537a6c35a1` 最终 `SUCCESS`，releaseTag=`release-20260629-1915-committed-head-v6`。manifest 已核对：
- 后端 commit=`e7af75e0102fe63161ae9ef18803b6d6c8f68c69`
- 前端 commit=`1ffcdca22b735df762a581b2eed207a4581e8a71`
- 两者 `dirty=false`

RED: committed-head-publish-test-20260629-v6 -> FAIL，真实 `publish-test` operation=`op-2026-06-29T112911230263400Z-bb754ec0-c5c7-4e3d-be60-36850080d278` 最终 `FAILED`。本轮已真实跨过：
- NAS 挂载、SSH、测试服 `.env IMAGE_TAG` 写入与校验
- 镜像包与 required SQL 上传
- `20260618_srm_d7_1_code_rule_baseline.sql`
- `车间主任 / mes_workshop_director` 动态主键插入

新的真实失败点收敛为 required SQL `20260629_mes_smart_scheduling_role_scope.sql`：
`ERROR 1062 (23000) at line 243: Duplicate entry '910239' for key 'system_role.PRIMARY'`

GREEN: committed-head-publish-test-20260629-v6-readonly-root-cause -> PASS，测试服 `172.30.30.58` / `ruoyi-vue-pro` 真实回查确认：
- `tenant_id=1` 已真实新增 `910240 / 车间主任 / mes_workshop_director`
- `tenant_id=1` 仍不存在 `班组长 / mes_team_leader`
- `system_role.id=910239` 已被历史角色占用，`code=doc_control`、`tenant_id=122`
结论：上一轮后端提交 `e7af75e0102fe63161ae9ef18803b6d6c8f68c69` 已修复 `车间主任` 主键冲突，但 `班组长` 仍硬编码 `910239`，因此同一 SQL 在测试服继续因历史主键占用失败。

GREEN: committed-head-backend-team-leader-id-release-fix-20260629 -> PASS，后端仓已以独立提交 `1e7e81f6f0264b960593610ce375a028059188c4` 修复 `20260629_mes_smart_scheduling_role_scope.sql`：将 `班组长 / mes_team_leader` 插入主键从固定 `910239` 调整为 `COALESCE(MAX(id), 910238) + 1`，并完成定向 pytest：
- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_mes_smart_scheduling_role_scope_sql.py -q` -> PASS，7 passed
- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_mes_smart_scheduling_role_scope_related_tabs_sql.py -q` -> PASS，3 passed
- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_mes_smart_scheduling_role_assignment_sql.py -q` -> PASS，3 passed

GREEN: committed-head-release-worktree-update-20260629-v7 -> PASS，维护控制台发布输入已切换到新的干净后端 worktree：
- 后端 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260629-1e7e81f` -> `1e7e81f6f0264b960593610ce375a028059188c4`
- 前端 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260629-1ffcdca` -> `1ffcdca22b735df762a581b2eed207a4581e8a71`
下一步：基于新的已提交 HEAD 重新执行真实 `build-release -> publish-test`。
RED: committed-head-build-release-20260629-v7 -> FAIL，真实 `build-release` operation=`op-2026-06-29T114728748007100Z-48b47bc9-db3e-4d71-a958-67f0a685dd90` 最终 `FAILED`，releaseTag=`release-20260629-2035-committed-head-v7`。本轮已真实完成：
- 后端 `mvn -f D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260629-1e7e81f\pom.xml -pl yudao-server -am -DskipTests clean package` -> `BUILD SUCCESS`
- 前端 `pnpm build:test` -> `Build successful. Please see dist-intruoyi-test directory`

新的真实失败点收敛为维护仓 Docker build context 契约：
`ERROR: failed to calculate checksum ... "/ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar": not found`

GREEN: committed-head-build-release-20260629-v7-root-cause-check -> PASS，只读核对本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260629-2035-committed-head-v7\docker-build-context` 后确认：
- 目录下仅存在 `yudao-ui-admin-vue3`
- `ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar` 不存在
- 维护仓 `ops/deploy/publish-int-ruoyi.ps1` 仍负责生成该 build context
结论：当前 blocker 不在后端业务仓，也不在测试服环境，而是维护仓 build context 生成逻辑未把后端 exec jar 带入 Docker 构建输入。
GREEN: committed-head-maint-release-context-fix-20260629 -> PASS，已在维护仓 `ops/deploy/publish-int-ruoyi.ps1` 收口 Docker build context 契约：
- 复制后端可执行包时显式写入 `docker-build-context/ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar`
- build context 准备完成后再次回读校验该文件必须存在，否则在 Docker build 前 fail fast
- 保持最终发布包仍会在 manifest 生成前删除 `docker-build-context`
GREEN: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py -q` -> PASS，4 passed。

GREEN: committed-head-build-release-20260629-v10 -> PASS，真实 `build-release` operation=`op-2026-06-29T131446009138100Z-4a88e7f8-e94c-4bfb-b199-4cc8e643c823` 最终 `SUCCESS`，releaseTag=`release-20260629-2118-committed-head-v10`。manifest 已核对：
- 后端 commit=`4f0553b9157ce385c536f763bebe7c082a2e2437`
- 前端 commit=`1ffcdca22b735df762a581b2eed207a4581e8a71`
- 两者 `dirty=false`

GREEN: committed-head-publish-test-20260629-v10 -> PASS，真实 `publish-test` operation=`op-2026-06-29T133100020181Z-7dd99be9-4a25-4760-a558-6ed03f35bef5` 于 `2026-06-29 21:43:18` 最终 `SUCCESS`。日志确认：
- `20260629_mes_smart_scheduling_role_scope.sql` -> `APPLIED`
- `20260629_mes_smart_scheduling_role_assignment.sql` -> `APPLIED`
- backend/frontend 容器重建启动成功
- 发布锁 `LOCK_RELEASED`

GREEN: committed-head-test-runtime-verification-20260629-v10 -> PASS，测试服 `172.30.30.58` 六项运行态验收全部通过：
- operation=`SUCCESS`
- manifest=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260629-2118-committed-head-v10\manifest.json`，后端 commit=`4f0553b9157ce385c536f763bebe7c082a2e2437`，前端 commit=`1ffcdca22b735df762a581b2eed207a4581e8a71`，两者 `dirty=false`
- 远端 `.env`：`IMAGE_TAG=release-20260629-2118-committed-head-v10`
- 远端运行镜像：`intruoyi-backend:release-20260629-2118-committed-head-v10`、`intruoyi-frontend:release-20260629-2118-committed-head-v10`
- 后端健康检查：`http://172.30.30.58:48081/actuator/health` -> HTTP `200`
- 前端首页：`http://172.30.30.58:8081/` -> HTTP `200`
