# 正式服原 MAIN 恢复控制安装

## 范围与依据
当前用户目标明确要求经 Spug 恢复到正式服并修复所遇问题；本安装实现必需的正式目标登记，不重复申请已有授权。实现 db64656f0adaee09eb21794b3bc4bd623bc7c23e，专属 release-db64656 干净副本构建 SAFE 包，123 文件逐 SHA/Python 编译通过，包 SHA c4d7e6c61bf1068d5c2125d006859d41308b6f139b7a327db3a8a73805a0615d。

后续归档视图保护正式实现为 bdd8aab86203a874e5c763d7c55f897d6a47c9a4，新的专属 release-bdd8aab 干净副本构建 SAFE 包124文件，SHA988bb1765e85a921d1a198d17ffe83f80f838ca6b66e667179dfad1e10a5fc32，文件清单SHA2937a241f948869a9d90391b550064f09fe047ddf5c50da5c424e33dd9e2a86c。旧db64656代次仅已追加文件，配置在只读预检失败前未写入，也未启动控制，原样保留。以下安装改为追加 engine-mainv2-bdd8aab，不覆盖旧代次。

## 执行顺序

UTC03:04修订：bdd8aab组件已成功追加，但配置安装在原MySQL无演练标签的资源观察阶段失败；已写owner/control配置保留，unit和target-installation尚无、replacement-state空/锁空闲/无预约、原195业务保持。根因已按完整MAIN身份修复并374项回归通过，限定提交9b3a298ce378b3ac565792a3bc3b92f1e5208898。后续从新专属release-9b3a298精确干净构建，追加engine-mainv2-9b3a298及该代次owner/control；同一replacement-state和现有完全相同的公共登记/凭据保持，不覆盖旧配置、不修改原容器标签。以下代次以9b3a298为准。最终需清理本任务三个专属构建副本，均无新提交/无需融合。
1. 只读核旧 staged installation、五原容器/镜像、全部容器运行基线、无预约、源锁空闲、NAS/fstab 和实际 xtables；旧代次保留。
2. 在现有控制根 /var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3 下追加 engine-mainv2-bdd8aab 与新配置/凭据。已追加的 engine-mainv2-db64656 原样保留。原 replacement-state 尚无操作，保持同一状态根；不能以新根绕过失败。
3. 从真实 Docker 当前状态生成 storage/v3 保留挂载和逐项停止历史消费者、MAIN/v2 配置/网络身份；Redis 无认证固定 ACL，MinIO 原发布端口全部纳入保护。只把三个 DATA 挂载列入 dataPaths，SQL/证据落 /var/lib/docker 盘。
4. 使用原来源控制的 Python3.12 与依赖，直接访问同机来源 127.0.0.1:32657，固定 History350 材料和共同 source.lock。正式控制绑定 127.0.0.1:43657，持久 LimitNOFILE65536；通过原生只读观察、实际来源准入、资源预算后，仅启动本任务新控制服务。
5. 验证全部原业务 PID/启动/配置、原 staged 材料、NAS/fstab 不变；追加本任务稳定 SSH 转发、本机已存在 Spug 的精确登记配置，仅重载该入口。保持 .58/.59 和其它来源/目标、历史/私密资料。

新增明确归档视图合同固定专用 CIFS 的 mountinfo 和实际 mount 程序 pin，安装仅只读预检；恢复持共同锁后才保护该视图，成功恢复原rw，失败保留ro和证据，不操作/mnt/nas或共享superblock。新增 Windows 转发只占43657，单独本任务登录启动项及稳定私密脚本；原42657来源及18557进度SSH保持，不停止或替换原转发。真实保留备份360终态前不抢源锁、不应用这些配置。

## 失败和验证
任一未知 writer、身份/挂载/网络/配置/端口/归档漂移、锁忙或预算不足立即停止对应动作，保留已追加控制材料，原业务不作补偿重启。安装不安装防火墙规则、不停止业务、不恢复数据。实际恢复前由正式执行器逐步安装围栏、停止原 writer、核停写，再执行数据库和对象替换；恢复失败保留停写及围栏，沿原操作和正式准许流程处理。

当前数据的新全备须先经真实 Spug 成功，并审核实际116文件SAFE完整SMB reader的原始全部载荷SHA/大小、前后树和元数据读回证据，之后才执行已固定350点到.57的覆盖；原RepositoryMinimumReadback/v1无payloadContentVerified字段，保持原schema，不改写历史。实际运行程序已独立定位并全部核SHA，不再按本地轻量源码推断，也不重复全量读取。实际恢复及业务验收、专属构建副本和测试资源清理另行记录；安装成功不作为目标完成。
