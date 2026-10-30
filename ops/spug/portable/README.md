# 在另一台自己的电脑使用 Spug 发布 IntRuoyi

本目录的代码可以提交 Git。导出的资料包包含 SSH 私钥、数据库口令、NAS 凭据、登录凭据和发布历史，**只在本地保存和复制**。

## 当前支持范围

- 在 Windows 电脑之间轮流交接 IntRuoyi 发布工作；通过本机 Spug 页面构建、测试、正式基线演练和三服发布。
- 执行器在普通 PowerShell 前台运行，不安装 Windows 服务。发布期间保持窗口和 Docker Desktop 开启。
- 迁移三服发布历史、当前版本及上一稳定版本的发布包、Spug 用户及配置、构建基础镜像。不会覆盖三服业务数据库、展厅或运行容器。
- 源码从已推送的 Git 提交精确下载，资料包不携带 Git 历史；无需依赖原电脑的 worktree 路径。
- 分贝通独立执行器和小程序执行器不在本次迁移范围内；对应入口明确显示未迁移。迁移副本停用原 Spug 的后台任务队列、监控和定时任务，防止两台电脑重复执行旧任务；发布中心使用独立执行器，不依赖这些旧队列。

**不支持两台电脑同时控制三服，也不能轮流使用各自过期的状态副本。** 切换电脑必须完成任务、停止旧执行器，并交接最新资料。旧电脑继续做过任何发布后，旧资料包即不能用于接管。此版本的交接由操作者确认，尚未实现跨电脑自动互斥。

未携带的旧包保留历史记录和清单，页面标识“仅可查看记录”，拒绝在新电脑直接重发或恢复；旧包文件仍保留在原电脑/NAS，不作删除。当前包和上一稳定包仅携带一份原包，导入时解包，避免重复携带镜像。

## 新电脑首次准备

安装并启动 Docker Desktop（Linux 容器），安装 Python 3.12+、Git、Windows OpenSSH、Java 21、Maven 3.9、Node.js 和 pnpm 9，以及 Google Chrome。把 java、mvn、node、pnpm、git、ssh、python 加入 PATH。首次配置 Docker/这些工具可能需要管理员权限；日常启动执行器不需要。

新电脑必须能访问 172.30.30.57、58、59、NAS 172.30.30.4 及构建依赖仓库。首次 Maven/pnpm 下载仍需要网络；资料包未包含全部依赖缓存。获取 GitHub 新提交时，如仓库要求认证，需在新电脑登录自己的 GitHub 账号；资料包不包含 Windows 凭据管理器。建议安装盘至少预留 30 GiB。不能把数据库备份目录当作代码发布包。

把整个本地资料包目录复制到新电脑，例如 `E:\SpugTransfer`；保留该目录。运行目录另选一个不存在的目录，例如 `E:\SpugRelease`。

旧电脑完成全部任务后，关闭旧执行器；目前旧电脑如仍使用服务，可在管理员 PowerShell 执行 `Stop-Service IntRuoyiReleaseExecutor`，并避免该服务在交接后自动启动。三服应用不受影响。导出后至停止前如有新任务，必须重新导出。

先校验资料包（只读）：

```powershell
python 'E:\SpugTransfer\portable\import_local.py' --package 'E:\SpugTransfer' --verify-only
```

首次导入：

```powershell
& 'E:\SpugTransfer\portable\install.ps1' -Package 'E:\SpugTransfer' -Destination 'E:\SpugRelease' -SourceStopped
```

如果 GitHub 必须经过代理，在安装命令末尾加 `-GitProxy http://127.0.0.1:实际端口`；请先确认本机代理端口，不照搬旧电脑配置。

脚本校验文件、恢复本机 Spug 数据、重写本机目录、导入镜像并保留发布历史。已有同名 Spug 容器或运行目录时停止，不覆盖。安装失败不要反复执行或删除目录，先查看失败步骤。

启动发布执行器：

```powershell
& 'E:\SpugTransfer\portable\start.ps1' -Root 'E:\SpugRelease' -SourceStopped
```

打开 `http://127.0.0.1:18080/release-center/?app=intruoyi`。Spug 账号保存在本地资料包 `private/spug-login.private.json`，不要将内容发到聊天或提交 Git。

## 发布操作

1. 在新电脑仓库 `E:\SpugRelease\repository` 获取 Git 上需要发布的提交；初始分支是资料包固定的 `portable-release`，不代表远端永远最新。
2. 在 Spug 选择 IntRuoyi，先查看三服实际版本，执行发布前检查；网络、磁盘、凭据、版本或状态有问题先处理。
3. 在“构建版本”选择明确提交，构建完整包；未提交修改不进入包。
4. 发布测试服，实际功能验证后标记通过；问题修复后生成新候选包继续测试。
5. 以正式服基线准备隔离环境，用同一个候选包演练并验收。
6. 正式服原地升级，验收通过并开放业务。
7. 使用同一包升级备用服并验收。失败保留原任务，根据页面恢复/续接入口处理。

关闭或刷新浏览器不会停止任务；不要在任务运行时关闭执行器窗口。当前资料包不会自动同步未来发布状态，下一次换电脑必须重新交接。

## 导出代码

`export_local.py` 用于从已准备的私密输入目录导出，不收集任意个人文件。参数需指向当前实际配置、源码仓库和新的输出目录：

```powershell
python export_local.py --inputs '<已整理的私密输入根目录>' --config '<当前 executor.private.json>' --repository '<本次指定提交的源码仓库>' --output '<新的本地目录>'
```

导出期间不发起新任务。导出会附带安装脚本、Playwright 工具、使用说明和文件摘要；若期间发布历史改变则失败，不能使用该输出接管。不要把早期原始 inputs.zip 当作安装包。
