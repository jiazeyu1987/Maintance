# 执行记录

- Closeout PASS：首次inline清理命令自身参数包含目标路径，被消费者保护拒绝，未删除；改为外置脚本后通过同一正式保护检查，5274 tracked文件确认，无新提交，git remove exit0，登记/实体目录均不存在。未跳过消费者检查。稳定执行器PID40124、cwd=C:/SpugHandoff/release/source/ops/spug/release-center、配置摘要保持，其他工作区/进程未动。最终completed。

- 开放JOB-b530c70f8e succeeded；公开8081实际登录/菜单/版本/打印认证复验PASS_WITH_OBSERVATIONS。独立运行态final-runtime.py通过，实际双镜像ID/tag、manifest、IMAGE_TAG及源码一致，UP/200/open；probe-print-network.py确认内部DNS、正式public-url、网络和403未认证拒绝正常。任务进入ready_for_closeout。
- Worktree命令记录：git worktree add --detach C:/SpugHandoff/release/promote-prod-print-20261123 624f6deb04a90bfff384ed576bb049166eb93f81；应用不构建，复用275c87011封包。验证命令：actions.py action check-prerequisites/promote-prod/accept-prod、helper-deploy.py transfer/deploy/verify、node menu-page-check.cjs及print-page-check.cjs、final-runtime.py、probe-print-network.py。命令均在本任务维护worktree编排；没有新提交，无需合回int_main。
- GREEN: experience-preflight -> PASS（本任务工作区清理）。固定repo=维护仓、path=C:/SpugHandoff/release/promote-prod-print-20261123、commit=624f6de；正式清理入口将核登记、clean、无新提交及无运行消费者，回执写外部目录；不动其他任务worktree或控制台。

- 正式晋级JOB-0ee3f179cb succeeded，远端OP-aa45ae21d6cce80feec3 succeeded；维护入口两项真实页面验收PASS_WITH_OBSERVATIONS，详见page-acceptance.md。打印新票据完成认证并显示服务器已连接。无未知/必需路径错误。
- GREEN: experience-preflight -> PASS（accept-prod开放）。已具备同包晋级成功、技术passed及本轮维护入口业务范围实测；按用户正式发布授权执行显式接受并开放，再独立复验公开8081入口及实际镜像/metadata/健康。只承认已列范围，不扩大为完整打印业务E2E。

- 助手镜像归档2926214656字节，SHA256 5ff357621f59e34304c5e649e4aa96476350aab833f94cf44f57a2882a571b52，正式load后ID与测试一致。首次容器启动探针遇连接重置，未重复替换；后续只读探针403正常。挂载比较首次因Docker返回数组顺序改变失败，逐字段核证为完全相同3项后改为按Destination排序比较，非放宽字段合同；只读验证最终PASS。正式新容器78b4a43ff306，旧容器保留为erp-invoice-voucher-print-assistant-before-prod-20261124（已停止）。3份助手源码哈希与测试证据完全一致；env、启动参数、挂载、端口、网络、restart策略均保持。

- 正式预检JOB-a40caf900b passed：原版本2026-11-23-08-35-27，指纹4e9c96799d60067479a70a7f38794f5ac7f6d6d58c2eca7f112a2d3dc4acda8f；原包/manifest摘要、tested流程阶段、SSH/NAS、UP/200、1.36TB余量、写入进程、恢复挂载、维护验收网络和目标升级计划均通过。只读预检不替代停写后的真实迁移复查。
- GREEN: experience-preflight -> PASS（主程序promote-prod及真实只读页面验收）。原测试包2026-11-23-22-02-22 / 275c870118f8096328d94bd38700455de3e76fc0；请求固定正式57，不执行backup59。先正式晋级、技术验收，再按真实页面结果开放。页面必要范围：真实登录、智能排产→排产工单真实列表、版本/变更说明、菜单搜索→发票凭证打印→正式18733受认证iframe。预先阻断业务写入，允许登录/captcha/临时打印认证票据；不以个人工作台写入或真实打印单据作为本次验收。

- 配置重载PASS：原PID14268→40124，稳定source路径未变，476源码文件保持，SQLite payload及435条job完全保持；原子字节/ACL探针及配置读回通过。
- 助手管理合同：正式systemd unit不存在，Docker unless-stopped管理；测试残留unit disabled/inactive而实际Docker unless-stopped，不启用旧unit。正式仅沿用既有Docker管理，不新建systemd。镜像标签的6287cc5不是OCI revision，OCI标签继承基础镜像，发布身份只认已验不可变sha256:8165fe79...及三份实际助手源码哈希。
- GREEN: experience-preflight -> PASS（助手镜像导出/传输/加载及同名服务替换）。冻结已验镜像ID；export本地SHA/目标SHA一致再load并核ID；留正式原inspect、镜像及已停止旧容器作为恢复依据，保留正式env、mounts、network、restart，不带测试业务数据；同名锁保护。根路径应403，实际身份/挂载/内部验票合同与正式原配置逐项核对后进入主程序晋级。部署失败保留现场并报告，不自动掩盖。

- 原包已自动技术验收并进入tested，test deployment JOB-2b57a4ae44技术passed；不重复mark-tested。恢复策略沿用已登记direct-three-server-v1 / external及原明确确认，非新增豁免。正式当前版本须由本次预检再次绑定。
- GREEN: experience-preflight -> PASS（正式公开打印地址登记/空闲执行器重载）。仅新增targets.prod.invoiceVoucherPrintAssistantUrl=http://172.30.30.57:18733/，先同卷原子替换及ACL探针，备份私密配置和SQLite，核无活动任务，原cmd/cwd/env重启，核payload不变；不改业务数据。

- 只读盘点：正式助手仍是2026-11-03-09-27-31，测试已验助手为2026-11-23-6287cc5-fixes / sha256:8165fe7917fea69e936eee00447f2bb1274cf4a8dd78fa158738cef2c5611a45。两环境均有独立正式目录/持久挂载及各自后端验票地址；正式profile缺invoiceVoucherPrintAssistantUrl，需要显式登记正式18733地址。只晋级同一不可变助手镜像，保留正式挂载/验票目标，不复制测试运行数据。
- GREEN: experience-preflight -> PASS（隔离维护工作区创建）。维护提交624f6deb04a90bfff384ed576bb049166eb93f81，目标C:/SpugHandoff/release/promote-prod-print-20261123；仅作本次发布编排和已提交合同验证，应用使用275c87011既有封包不重构建。无新提交时发布后删除，不动并发工作区。

- 用户授权：发布正式服务器，也包括打印助手。前序任务已completed；创建本任务，先只读核验正式发布和独立助手边界。
- BDD: Given 同包已在测试服通过基础及打印入口验收；When 按正式门禁晋级并部署正式助手；Then 正式版本与包一致、打印入口真实认证成功，保留环境专属配置与恢复依据。
