# IntRuoyi Codex 发布执行检查清单

## 触发条件

当任务涉及以下任一事项时，Codex 必须先读本文，再决定是否进入真实发布动作：

- 运行控制台 `build-release`
- 发布到测试服
- `mark-tested`
- 发布到正式服
- 发布到备份服
- 发布失败后的重试

本文面向 Codex 执行，不替代正式规则。正式边界仍以以下文档为准：

- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`

## 执行模型

Codex 必须把完整发布任务视为以下严格顺序：

1. `build-release`
2. `publish-test`
3. 测试服运行态验证
4. `mark-tested`
5. `promote-prod`
6. 正式服运行态验证
7. `promote-backup`
8. 备份服运行态验证

任何一步失败，都必须先记录真实证据，再修复，再从合适步骤重新执行；不得把不同 releaseTag 的成功结果拼接成一次完成。

## 0. 开始前必做

### 必做动作

- 创建或识别任务目录。
- 读取 `docs/experience-index.md`。
- 命中并读取：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 如涉及登录验证，再读 `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
- 在 `execution-log.md` 先写 `GREEN: experience-preflight -> PASS` 或明确 blocker。
- 在 `docs/request-command-log.md` 记录用户需求与关键命令。

### 放行条件

- 任务目录存在。
- 命中文档已读取并在任务文档写出 `经验门禁`。
- 高风险动作前已有 `experience-preflight` 记录。

### 阻塞条件

- 没有任务目录。
- 没有 experience-preflight 记录。
- 正式服或备份服操作缺少当前任务授权。

## 1. 构建前检查

### 必做动作

- 确认发布源头在 `D:\ProjectPackage\Int\IntRuoyiMaintance`。
- 确认后端、前端、维护仓三方主分支名、当前提交与 dirty 状态。
- 每次发布一律先创建本次专用的临时发布 `worktree`，禁止直接在主工作区执行构建、验证或发布。
- 必须先核对测试服当前 releaseTag/manifest 与本次目标提交是否一致；不一致时不能复用旧发布结论。
- 必须显式核对 runtime-control 当前 `repo-root` / `frontend-root` 指向的就是本次最新临时发布 worktree，而不是主工作区或旧 worktree。
- 在临时发布 worktree 上先过前端 lockfile / 依赖恢复与后端目标模块构建门禁；未通过时，先提交修复再重建 worktree。
- 先跑发布门禁或契约测试，尤其是：
  - migration policy gate
  - 影响发布链路的 SQL 契约测试
  - 影响产物契约的发布脚本测试
- 确认本机运行控制台是当前版本，必要时重启后再核对。
- 核对构建预览命令包含：
  - `-Mode build-release`
  - `-Component intruoyi`
  - 本次目标 `releaseTag`

### 放行条件

- migration / manifest / 脚本契约未报错。
- 本次使用的后端、前端、维护仓输入关系清晰。
- 三仓主分支状态、本次目标提交与临时发布 worktree 路径已明确记录。
- 运行控制台预览命令指向正确 repo-root / frontend-root / scriptPath。

### 阻塞条件

- SQL 缺少 `release-migration` 元数据。
- `dependsOn` 错误。
- 发布脚本仍引用旧产物名、旧变量、旧路径。
- 运行控制台仍加载旧 worktree 或旧逻辑。
- 临时发布 worktree 自身无法通过 frozen-lockfile、依赖恢复或目标模块构建门禁。

## 2. 构建完成判定

### 必做动作

- 检查 build operation 最终状态。
- 读取 manifest。
- 核对：
  - `releaseTag`
  - backend commit
  - frontend commit
  - `sourceRepos.dirty=false`
  - manifest 中 `branch` 仍是本轮计划分支，且未在构建过程中漂移到新的未计划 commit
- 若任务要求“只发布 Git 已提交版本”，必须把 manifest 视为最终发布输入证明；构建前的 `git status clean` 不能替代构建后的 manifest 校验。

### 放行条件

- build operation=`SUCCESS`
- manifest 存在
- manifest 与本次目标 releaseTag、提交、发布范围一致

### 阻塞条件

- 只看到页面成功提示，但无 manifest
- manifest 与本次提交或 releaseTag 不一致
- `dirty=true`
- 构建完成后 manifest 记录的 commit 与构建前计划值不一致

## 3. 测试服发布与验证

### 必做动作

- 预览测试服发布命令，确认：
  - `-Environment test`
  - `-ServerHost 172.30.30.58`
  - `-RemoteAppDir /opt/intruoyi/runtime`
- 执行 `publish-test`
- 只读核对测试服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- test operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- operation 未成功
- `.env` 已变但容器镜像仍是旧版本
- health 不通
- frontend 不通

## 4. mark-tested 放行规则

### 必做动作

- 只有在测试服验证通过后，才允许执行 `mark-tested`
- 记录 operation ID、结果与 recovery candidate

### 放行条件

- 测试服运行态验证已完成
- `mark-tested` operation=`SUCCESS`

### 阻塞条件

- 测试服未验证就尝试 mark-tested
- 手工改 tested 状态代替 action

## 5. 正式服发布与验证

### 必做动作

- 预览正式服发布命令，逐项核对：
  - `-Environment prod`
  - `-ConfirmText PROD`
  - `-RequireTested`
  - 目标 host、目录、数据路径、MinIO 参数
- 执行 `promote-prod`
- 只读核对正式服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- prod operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- 正式服未带 `PROD`
- 正式服未带 `RequireTested`
- operation 未成功
- `/mnt/nas`、数据盘、MinIO、挂载状态异常

## 6. 备份服发布与验证

### 必做动作

- 预览备份服发布命令，逐项核对：
  - `-Environment backup`
  - `-ServerHost 172.30.30.59`
  - `-RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases`
  - `-RemoteDataRoot /mnt/intruoyi-data/runtime-data`
  - `-RemoteDataDiskMount /mnt/intruoyi-data`
  - `-RemoteDataDiskDevice /dev/mapper/cl-home`
  - `-RemoteMinioContainer intruoyi-minio`
- 执行 `promote-backup`
- 只读核对备份服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - 数据盘挂载
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- backup operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- `/mnt/intruoyi-data` 挂载正确
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- 备份服未显式使用 `/mnt/intruoyi-data`
- 备份服误继承 Docker 根目录路径或正式服参数
- operation 未成功

## 7. 失败时的排查优先级

Codex 必须按这个顺序排查：

1. migration / manifest / required SQL 契约
2. 维护仓发布脚本与业务仓产物契约
3. 运行控制台当前加载版本
4. 测试服 / 正式服 / 备份服环境状态

禁止在第 1、2 层未排干净前，直接把问题归因到服务器。

若失败点在 required SQL：

1. 先只读回查真实库状态、主键占用、历史数据与 tenant 范围
2. 再决定修 SQL、修迁移契约还是修发布脚本
3. 禁止手工改测试库绕过发布门禁

## 8. 完成判定

Codex 只有在以下条件同时成立时，才能判定完整发布完成：

- 同一 `releaseTag` 已走完 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`
- 五个 operation 都有明确结果证据
- 测试服、正式服、备份服三环境都已验证：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health=`UP`
  - frontend HTTP=`200`
- 任务日志与请求命令日志已回写

任何缺项都不得宣称“完整发布已完成”。
