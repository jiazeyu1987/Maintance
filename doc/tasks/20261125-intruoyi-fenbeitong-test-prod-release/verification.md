# IntRuoyi 测试与正式发布验收

用户要求的两服发布及运行态、真实页面验收已通过，本任务自有工作区清理及本地运行路径核验已完成。最终收尾证明见 local-closeout-proof.json，任务状态 completed。

版本 `2026-11-26-01-52-12`，源码 `eb866bbaf4ea1b1c6db93daa63e77576766c3684`。

| 项目 | 测试服 172.30.30.58 | 正式服 172.30.30.57 |
| --- | --- | --- |
| 部署任务 | JOB-ea115d06b9 succeeded | JOB-9bf24c43bb succeeded |
| 远端部署 | OP-a0ba82e7c8e1222f67c0 succeeded | OP-968efedbe5fbf6f10546 succeeded |
| 正式开放 | 不适用 | JOB-65c04bddbe succeeded |
| 后端 / 前端 | UP / HTTP 200 | UP / HTTP 200 |
| IMAGE_TAG、manifest、双镜像 | 全部与本轮包一致 | 全部与本轮包一致 |
| 维护及开放/来源绑定pending | false | false |
| 数据库合同 | 迁移后、后端开放前、公共入口开放前均PASS | 同左 |
| 真实页面 | 登录、排产读取、分贝通认证、版本说明通过 | 维护入口及普通8081入口均通过 |

同包构建 JOB-1486fa339e、测试标记 JOB-b458ccb56f 均succeeded。包SHA256 `74357f22c93cb3db8e98cd3cc217f36ddc18f4d28afb2717dc396447dc1147f3`；manifest SHA256 `b3b960c270ebec0a5594c75aee2d02e07739705004a1f1af99c38f1368d3976b`。两服后端实际镜像ID `sha256:4825fe1571a18e634066c2d9927ecc4e7f6595fc24027fa992de195239a3f675`，前端实际镜像ID `sha256:462ac2f7377973951734aa20d5373afef4a3a30c20aa83fbee55ee4082d503e6`。

## 修复与验证

- SQL登记修复提交6a099294a：只补正式发布登记和同名只读预检，不修改不可变旧迁移。真实RED复现未登记拒绝，2项登记测试、633项菜单检查、919迁移/1244资产计划及两服真实只读预检通过，错误权限反例正确拒绝。
- 分贝通修复提交eb866bbaf：票据携带可信签发租户，匿名校验只在该租户上下文读取金蝶配置并恢复原上下文；缺失/非法租户明确拒绝。先复现线上同类NullPointer，后续67项JUnit失败/错误/跳过均0。两项实现均已融合int_main并核对应文件与主线端口guard，无关修改保持。
- 维护执行器配套安装：从提交字节安装运行agent，24项配置回归通过；私密配置、477项非目标文件及463项既有任务payload保持。只重载空闲且身份确定的普通执行器，保持稳定路径。
- 实际构建命令：正式入口 `control.py action build-release build-r3.json`，绑定最终提交并新建独立构建worktree；后端Maven生产构建、前端Vite生产构建、镜像内版本和封包后端合同、原包/NAS封存通过。主工作区脏文件没有进入构建输入。
- 真实页面使用Playwright 1.63.0与实际Edge、受保护配置的芋道源码/admin。排产返回实际空列表，不制造业务数据；分贝通状态地址分别指向本服18734，实际票据回调成功，实际JVM内外助手地址核验通过。版本按钮和非空变更说明与最终提交绑定。
- 每个入口排产6项、分贝通8项观察逐条审阅，原始证据SHA及具体归因见对应page-acceptance.json/observation-review.json；没有静默忽略未知错误。正式脚本冗余networkidle等待的真实失败已保留，改用请求结束状态与实际可见控件后，两服回归通过。

## 已知事项与范围

两服现有助手尚未保存费用报销字段对应关系，GET config返回400，真实映射面板显示NOT_CONFIGURED；实际两服相关助手源码一致，本次未修改助手或保存财务配置。后续使用财务同步、生成报销单和记账前需确认业务映射，本次不将认证入口验收宣称为财务业务验收。详见helper-config-observation.json。

部分租户注册证提醒缺负责人/期限配置。正式旧版本在本次升级前已有同类失败，证据独立保留；本轮未修改业务配置。

百度统计脚本网络关闭、顶部装饰头像ORB拦截及预声明的工作台写请求拦截均有具体归因。各分贝通观察窗口末尾刚发起的工作台来源目录GET未取得响应，明确记为范围外未验证；工作台初始化/目录及完整业务E2E没有放行。没有进行财务、业务数据写入或审查服发布。

本任务仅完成用户明确要求的测试服与正式服，不声称含审查服的全链路发布已完成。正式恢复沿已登记external责任确认执行，不冒称本轮创建或验证了额外正式全备。

## 历史与证据

初始包2026-11-25-23-53-05因SQL未登记构建失败；第二包2026-11-26-00-12-02部署测试成功但分贝通认证503，未mark-tested或晋级。最终结论只使用最后一包，不拼接不同releaseTag。旧失败、原始回执及诊断JSON已独立封存。

机器可复核结果见release-result.json。页面报告为test-page-acceptance.json、prod-maintenance-page-acceptance.json、prod-page-acceptance.json；mark-tested时原报告另存at-mark-tested。原始含业务数据、日志或配置的证据仅保存在受保护私密目录，未进入Git。

## 本任务工作区账目

下表路径均位于 `C:/SpugHandoff/release/`，没有复用其它任务工作区。实现验证与融合先于破坏性清理，最终物理/Git登记删除结果由对应cleanup-proof及local-closeout-proof记录。

| 相对路径 | 目标提交 / 新提交 | 构建或验证入口 | 融合和删除证明 |
| --- | --- | --- | --- |
| build/2026-11-25-23-53-05 | e1ccafbc6，无新提交 | control.py action build-release build.json；SQL登记门禁正确拒绝 | 无需融合；failed-build-cleanup-proof.json |
| build/2026-11-26-00-12-02 | 6a099294a，无新提交 | control.py action build-release build-r2.json；正式构建与镜像合同通过 | 无需融合；构建任务自动核25300文件/3128链接并删除 |
| build/2026-11-26-01-52-12 | eb866bbaf，无新提交 | control.py action build-release build-r3.json；正式构建与镜像合同通过 | 无需融合；构建任务自动核25300文件/3128链接并删除 |
| registration-config-release-fix-20261126 | e1ccafbc6 -> 6a099294a | test_release_source_registration.py、verify-plan.py、真实两服只读预检及菜单检查 | 已融合int_main；source-fix-cleanup-proof.json |
| fenbeitong-ticket-tenant-20261126 | 6a099294a -> eb866bbaf | Maven定向67项JUnit，命令见下文；融合文件比对和端口guard | 已融合int_main；tenant-fix-cleanup-proof.json |
| intruoyi-fenbeitong-release-20261125 | ea06ce898，无新提交 | 独立维护24项配置回归；原子安装探针及受保护数据保持 | 无需融合；maintenance-cleanup-proof.json |

租户修复实际验证命令（cwd为修复worktree的IntRuoyiBackend）：

`mvn -q -Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8 -pl yudao-module-system -am -Dtest=FenbeitongAssistantServiceImplTest,InvoiceVoucherPrintAssistantServiceImplTest,AuthControllerTest -Dsurefire.failIfNoSpecifiedTests=false test`

维护24项配置测试的复现入口（cwd为维护源码ops/spug/release-center）：`python -X utf8 -B -m unittest test_fenbeitong_integration_config test_fenbeitong_runtime_url test_invoice_print_runtime_config test_clone_network_config`。此处列供复核，不以事后重跑替代最初独立维护worktree实际PASS证据。

## 最终收尾

- failed-build：正式清理器通过，逐字节核25299项受控文件、拆除0项生成链接；Git登记和物理目录均已删除。
- source-fix：正式清理器通过，逐字节核25300项受控文件、拆除0项生成链接；Git登记和物理目录均已删除。
- tenant-fix：正式清理器通过，逐字节核25300项受控文件、拆除0项生成链接；Git登记和物理目录均已删除。
- maintenance：正式清理器通过，逐字节核5348项受控文件、拆除0项生成链接；Git登记和物理目录均已删除。

维护工作区首轮因两个未知缓存被保护拒绝；后续核tracked源码、pyc头部与完整marshal编译结果逐字节相同，私密保留原缓存后仅精确删除这两个派生文件，再走原清理器通过。没有扩大清理白名单。详见maintenance-generated-cache-proof.json。

两次成功构建目录已由构建流程自动校验并删除，加上上述4个目录，本任务6个工作区均无残留。SQL/租户修复提交均已融合int_main，维护及构建目录无新提交。本任务slot9/10仅在端口无监听、其它登记保持后释放。稳定执行器PID 29472的入口、配置参数及cwd与稳定路径一致，运行agent符合已提交字节，私密配置摘要保持；没有停止或清理其它任务资源。
