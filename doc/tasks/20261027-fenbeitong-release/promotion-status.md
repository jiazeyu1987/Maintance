# 正式服与审查服发布请求

状态：in_progress（2026-10-27，Codex重启后续做）。用户已授权补齐接入并发布分贝通到正式服和审查服；尚未执行目标发布。

候选包：2026-10-27-10-03-10，当前 test-deployed，无测试验收及正式演练证据。测试服助手容器已经完成技术部署检查，不代表业务入口已可用。

通过 Playwright 使用用户既有授权的芋道源码/admin，只读登录测试服 172.30.30.58:8081，依次点击 ERP系统 → 财务管理 → 分贝通凭证。实际 URL `/erp/finance/fenbeitong-voucher`。页面明确报错：

> 分贝通费用报销助手地址未配置，请配置 VITE_FENBEITONG_ASSISTANT_URL。

未出现助手 iframe，也未触发真实业务操作。证据在 `E:/Int/CacheData/fenbeitong-release/promotion-20261027/business-entry.json` 和 `business-entry.png`。

后续必须先修复 IntRuoyi 与独立助手的接入配置，经过正常前端构建发布使入口可用，并核实后端助手健康探测与票据校验路径。不能在运行中的前端容器临时补文件，不能改状态库伪造验收，不能通过 API 自签票据绕过真实入口。

本轮未点击测试验收通过、演练通过、正式发布或审查发布；未修改三服应用与业务数据。发布请求仍未完成，需解除这一具体前置条件后继续原包或明确的新包流程。

## 接入修复进展

- 从当前三服实际版本的源码提交 9a6ad209b 创建独立干净 worktree `E:/Int/CacheData/fenbeitong-release/intruoyi-integration-source`。只修改已有分贝通页面、测试/生产环境地址配置及针对性测试；不带入主工作区未提交改动，不新增或修改 SQL。
- 新提交 b68acd4c5f7b6edb5db56d22f344d3483b282e64 将明确地址模板 `http://{hostname}:18734/` 按当前浏览器服务器解析。同包在三服分别连接各自助手；空配置仍报错。原绝对地址配置正常解析。菜单检查、提交 hook 和地址行为检查通过。构建源码缓存已固定到此提交。
- 发布执行器在目标显式配置 `fenbeitongAssistantHost` 时，把正确主机作为 Spring 启动参数写入后端容器，保留既有参数；隔离环境禁止配置真实助手地址。60项相关回归通过。用户已加载第一版修复，服务源为 intruoyi-executor-integration-v1。
- 通过真实 Spug 按钮创建 IntRuoyi 构建 JOB-c2358a09e8，releaseTag=2026-10-27-10-56-21。该任务在 migration-policy-and-history 失败：Windows服务的 sys.executable 是 pythonservice.exe，不能作为普通脚本解释器。未开始编译或远端部署。原失败证据保留。
- 已在构建器增加 Windows服务专用的明确 pythonExecutable 配置，拒绝 pythonservice.exe 或缺失配置；控制台仍使用当前解释器。29项构建及接入配置测试通过。新冻结运行目录 intruoyi-executor-integration-v2 已准备，现有其他402个源码身份保持可核对。
- Windows服务更新要求管理员，当前会话无此权限；已请用户再次运行 update-integration-service.ps1 加载第二版修复。收到运行结果并核对后，从 Spug 重新构建，不复写失败包、不伪造原任务成功。

## Codex重启后续做

- 用户已执行第二版服务更新，实际服务源为 intruoyi-executor-integration-v2，配置包含正确 pythonExecutable 和三服助手主机。
- JOB-1e4d869d85（2026-10-27-11-10-14）已编译完成前后端，但本机内存压力导致 state_store 保存时 MemoryError，任务状态停留在 compile-frontend，工作线程已退出，没有创建完整镜像包或部署远端。服务日志有明确异常栈；不把现存 dist 与 JAR 当作已完成发布包。
- 通过既有普通操作用户服务权限重启本地执行器成功，无需再次要求管理员；原任务自动标为 interrupted。Playwright在真实Spug页面执行 inspect-interruption JOB-11b09603c8 和 reconcile-interruption JOB-15f4588a3a，核对原进程身份及未部署事实，保留原失败记录后关闭尝试。
- 已依据本机实际Vite实现，在任务源的 terserOptions 明确设置 maxWorkers=2，避免默认按CPU核数展开压缩工作进程的内存峰值。提交 cccf308e068d29b26757944521800092c00f2917；正常提交hook通过，没有绕过检查或改变业务逻辑。
- 已由Spug按钮重新创建构建 JOB-3a502e3953，固定上述提交；正在构建。后续动作必须使用本次成功构建的新tag，不再使用未封包的2026-10-27-11-10-14。

### 接续状态（Codex重启后核实）

- JOB-3a502e3953 已成功构建，发布包版本 2026-10-27-13-12-40。
- 测试首发 JOB-eb798dd338 在恢复点导出后、封存恢复记录阶段失败，原因为数据库名验证正则拒绝合法名称 `ruoyi-vue-pro`，尚未执行迁移或替换容器。恢复资料不完整封存，不据此自动删除或重放。
- 已确认测试容器原 ID、镜像和业务数据容器不变，迁移记录行数为0；原测试 backend、frontend、Redis、MinIO 已启动。后端UP，前端200，read_only与super_read_only均为0，当前版本结构与原指纹一致。恢复SQL和两个卷归档保留在原包目录。
- 执行器新增合法数据库名连字符支持、封存前的检查，以及严格绑定原操作回执、原容器ID、原指纹和未封存恢复资料的 capture-not-sealed 恢复证明。119项定向回归通过。
- 原任务失败后通过真实 Spug UI 核对并显式关闭，JOB-a60df5a80e成功；未伪造原任务部署成功或改变迁移记录。
- 同包重试 JOB-65157b72e7 已按原 deploy-retry 层级分离在 `.../test/packages/attempts/JOB-65157b72e7`，恢复资料生成成功，测试版本目标仍为 2026-10-27-13-12-40。当前观察到动作已到技术登录检查并失败；失败原因尚待确认。页面真实登录授权与按钮验收尚未通过，因此不可进入正式或审查发布。
