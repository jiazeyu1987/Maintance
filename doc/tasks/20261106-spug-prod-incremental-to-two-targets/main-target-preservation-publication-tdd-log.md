# MAIN目标保留阶段2：严格发布与持续交接TDD

## Current Status

ready_for_closeout（2a本机实现已冻结，待父限定提交）；2a完整材料发布、独立严格SMB读回、durable hold及archive-proof已获得本阶段真实Linux正向和负向证据。2b handoff/stage/首clear/producer历史验收尚未开始；真实包、58/59登记、服务器、NAS与覆盖仍HARD HOLD。父已批准本机隔离Linux真实RED→GREEN和相关回归；不得构建发布、访问真实Docker业务socket/服务器/SMB、提交、清失败材料或重派原376/UNKNOWN。

## 目标、里程碑与预期验证

- 2a-1：冻结下述精确schema/API与认证方法SHA；新增有限BDD失败测试，实际Linux取得业务RED。
- 2a-2：最小实现共享严格SMB方法、typed材料出版、仓库持有/角色和archive-proof；真实LinuxGREEN、受影响旧合同回归后冻结交父审diff。
- 2b：父审2a后另行开始同session handoff与完整MAIN接线，不以2a代替clear准入。

预期验证保留真实临时文件、进程、flock、ctx/custody、Publisher.stream、SMB严格reader和binder；SMB/SQL/Docker只在明确有限协议边界，不声称实际业务恢复。每轮唯一命名快照、固定Python镜像/离线wheels、networknone/只读根/no-cap、原/副本SHA前后、JUnit/raw日志/实际容器删除均落原件。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；缺失/漂移/unknown/任意非法hold一律拒绝，旧普通LIGHT路径保持，MAIN不能借LIGHT弱合同。
- 是否从根因和长期维护角度解决：是；一套严格SMB算法与原Publisher/binder；显式角色、原operation和同ctx，不创建新worker/源控制服务。
- 是否存在临时补丁或绕过：否；不skip_restore、不伪sourceRestored/READY、不改旧point原件或静态policy逐次塞hold。

## 经验门禁

- Trigger：覆盖前保留FULL、仓库字节发布/完整读回、同锁/保护连续。
- Preflight check：准确实际模块路径、认证方法SHA、原ctx/flock/Budget/预约、材料真实所有权/完整树、SMB认证/加密/新会话与缓存、输出根边界/容量、仓库read guard/unknown/hold。
- Blocker：缺原件/漂移、metadata-only、无真实终态、预算/锁丢失、角色未排除普通baseline、未完成或非法hold。
- Verification：真实Linux零skip、源/副本前后SHA、完整正向与有限负例；普通FULL三生命周期和SAFE保持点按实际入口回归。
- Forbidden action：不真实NAS/服务器/业务Docker/远端，不构建安装/提交，不清失败材料，不把MATERIAL_COMPLETE或archive-proof当可覆盖。
- Evidence：父阶段2授权、publication-plan、阶段1r6 12PASS和r8非archive194+r9 SAFE archive17分轮原件。

## 精确schema与API（2a冻结）

全部JSON用duplicate-key拒绝解析、exact字段集合、原pin字节/摘要验证；原件O_EXCL/0600、目录0700、无link且有界。时间是UTC，pin为精确path/bytes/sha256。原policy/owner/材料不改写。

`MainTargetPreservationPolicy/v1`字段：`schemaVersion,targetConfigRef,captureRef,captureConfigurationPin,repositoryConfigurationPin,backupEpochPolicy,maxArchiveBytes,maxReadbackRecordBytes,maxPreservationSeconds,minimumFreeBytes`。数值均正整数。owner的`targetPreservationPolicies[targetRef]`是该原件pin；capture基线pin等于原targetProgramPolicies登记，实际活动pin来自真实ctx evidence；backupEpochPolicy全等。

现`MinimumConfiguration`没有独立严格schema且构造依赖UI request，MAIN不制造该请求。新`MainTargetPreservationRepository/v1`是对原仓库材料的显式typed引用，字段：`schemaVersion,repositoryId,repositoryRoot,sourceIdentityPin,captureBinderPin,readbackConfigPin`。readbackConfigPin直接核原`RepositorySmbReadbackConfig/v1`（含原credential/library pins，recordRoot必须本次publication目录）；binder为原正式文件pin，不能任意callback。这里只新增配置合同，不新建仓库/凭据/服务或改原普通配置。

`MainTargetPreservationIntent/v1`字段：`schemaVersion,operationId,targetConfigRef,role,policyPin,repositoryConfigurationPin,configurationPin,requestPin,originalTargetPin,captureConfigurationPin,executionBindingPin,reservationPin,contextPin,readyEventPin,replacingEventPin,archivePath,deadlineMonotonic,createdAt`。role固定`TARGET_PRE_RESTORE`，所有上下文由真实typed session取得。

父在本轮静态审查明确：**旧originalExitEvidencePin的RepositoryOriginalExit/v1语义绝不改**。本TDD以下专用point合同取代设计初稿的普通point/v1方案；不改原point/native Catalog.evidence，也不让它们解释新角色。

`MainTargetPreservationPoint/v1`字段：`schemaVersion,role,backupId,generationId,pointType,parentPointPins,commonRecoveryPoint,payloadRefs,manifestPin,readbackEvidencePin,archiveCloseEvidencePin,captureTerminalEvidencePin,integrityState,controlledRestoreEligible`。role固定TARGET_PRE_RESTORE、pointType=FULL、parents=[]、integrityState=COMPLETE、controlledRestoreEligible=false。**没有originalExitEvidencePin**。唯一文件为`repositoryRoot/preservations/<operationId的sha256>/.repository/preservation-point.json`；与普通archives分离，普通Catalog/自动基线根本不枚举此目录，不添加旧schema宽容分支。载荷布局、RepositoryManifest/v1、binder/RecoveryMaterial/ObjectContentIndex算法仍复用。

`MainTargetCaptureTerminal/v1`字段：`schemaVersion,operationId,targetConfigRef,materialsPin,nativeEvidencePin,sourceRestored,writersRemainQuiesced,finishedAt`。nativeEvidencePin是材料完成时真实MainNativeExecutionEvidence/v1快照，所有实际捕获子进程终态已知且无pending；sourceRestored=false、writersRemainQuiesced=true。不声称原MAIN编排进程已退出，不伪造actualExitCode0/processTerminated。

`MainTargetPreservationHoldIntent/v1`字段：`schemaVersion,repositoryId,operationId,targetConfigRef,role,archivePath,pointPath,preservationIntentPin,createdAt`。固定仓库`.repository-control/preservation-holds/<operationId>-intent.json`，先于目标目录/载荷写，路径必须preservations唯一直接子目录且pointPath为该目录`.repository/preservation-point.json`。

`MainTargetPreservationHold/v1`字段：`schemaVersion,repositoryId,operationId,targetConfigRef,role,intentPin,pointPin,archiveProofPin,createdAt`。固定同目录`<operationId>.json`，只在archive-proof已严格完成后写。无终态intent也持有；malformed/link/额外文件/错scope不当成无hold；无自动release。

`MainTargetPreservationArchive/v1`字段：`schemaVersion,state,operationId,targetConfigRef,role,intentPin,materialsPin,holdIntentPin,pointPin,manifestPin,payloadTreePin,repositoryBindingPin,recoveryMaterialPin,objectContentIndexPin,readbackPin,sidecarReadbackPin,archiveClosePin,captureTerminalPin,payloadContentVerified,serverDurabilityVerified,independentFailureDomain,originalResultPins,finishedAt`。state固定`ARCHIVED_VERIFIED`，payloadContentVerified严格true，durability/failureDomain严格false。仅2a材料归档证明，**不含handoff/不允许stage/clear**。为避免循环，hold终态引用本archive-proof；后续最终preservation result才引用hold终态与handoff。

`MainTargetPreservationFailure/v1`字段：`schemaVersion,operationId,targetConfigRef,phase,failureCode,mutationDispatched,terminalUnknown,originalResultPins,finishedAt`。首失败独占冻结；已知archive-proof存在后不重写；外层unknown保守汇总。

2a API：

```python
TargetPreservation.prepare(native, *, policy_pin, reservation_pin) -> TargetPreservation
TargetPreservation.capture_and_publish() -> archive_proof_pin
TargetPreservation.check()                  # same ctx/lease/files/deadline/hold
TargetPreservation.close()                  # local resources only, no deletion/release
validate_archive(native, archive_proof_pin) -> VerifiedPreservationArchive
publish_materials(configuration, materials, *, publication, deadline) -> archive_proof_pin
preservation_holds(config, *, guard) -> held_point_paths
```

`publish_materials`位于现repository_minimal；严格检查`publication`为同模块实际TargetPreservation、`materials`为其session真实CapturedMaterials，不接受caller bool/成功dict。普通publish函数原行为不变。2b最终`preserve`/handoff API暂不实现，archive-proof不能自授权。

SMB共享：在repository_native_readback新增共享`read_verified`与严格`PreservationReadback`，默认SmbReadback.read原LIGHT字节不改；共享函数按认证SAFE方法逐句搬移，仅方法归属/self调用边界调整。认证基线`backup-restore-standard-20261021.tgz`中SmbReadback.read统一LF后完整方法SHA256：`c8deb5e5df474e497aafbe6c7da9d33058240e5fc8495296b7922486adaba268`。实际SAFE构造接这一个实现留后续包装里程碑，当前不修改standard_fixes或成员；认证五具名变换/五采集保持点全部保留。

## BDD与首轮RED范围

1. Given同真实ctx/custody/flock的当前MAIN材料；When真实Publisher/strict SMB/binder完整发布；Then专用FULL preservation point、全部原始读回、durable hold及archive-proof真实产生，普通point/v1和originalExitEvidencePin合同不变，flags1/1/paused/原保护保持，stage/clear仍拒绝。
2. Given本地完整字节/有限独立SMB协议；When expected错、内容/同内容inode漂移、读中大小漂移、额外/缺文件、link、认证拒绝或预算到期；Then严格方法/完整readback拒绝，不写完成proof/hold，不合成或重传。
3. Given已登记policy；When ctx/native/原件/pin/捕获基线/epoch/仓库scope错或未知；Then首新增出版写之前拒绝。
4. Given仓库已有hold intent/完整hold；When retention重新规划/删除或普通baseline选择；Then保留点受保护且不作普通baseline；坏/未完hold阻断破坏动作，重复同operation不覆盖原件。
5. Given普通LIGHT/source默认入口和认证原方法；When新strict入口加入；Then原默认方法/普通FULL恢复生命周期不变，严格方法与认证SHA边界一致。

首轮新增测试先冻结再运行；实际RED原因/exit/JUnit/源pins逐轮追加，载体错误单列，不伪称实现失败。2a通过后立即冻结交父，不提前2b。

## 实际记录

2026-11-10：只读核出上述认证方法SHA；已创建本先行TDD。尚未写产品实现、尚未运行本阶段测试。

首轮11项候选测试已冻结：`test_recovery_target_preservation.py`11083B/a45c2c952231274f9b3d617fca124b468b8ecd6b6cdb987e3b74dea7ca9750b4；本机compile实际exit0，不是测试结论。载体`PRIVATE/run-target-preservation-2a-local.py`6798B/d35b2473007654f3c1dc12e16e0c56255a86f54714e448f1ffa429d4383b5073，独占label原件、父r6批准输入集合当前实字节+新测试/模块、同固定Python镜像和12离线wheels。命令意图：`python -X utf8 PRIVATE/run-target-preservation-2a-local.py --label red-20261110-r1`，只隔离本地协议测试，无Docker socket/NAS/业务挂载。GREEN: experience-preflight -> PASS（本地隔离权限/输入/真实Linux与失败保留已核；非服务器或真实备份授权）。

RED r1实际11FAIL/0ERROR/SKIP，pytest exit1，outer30.796秒；6项明确缺PreservationReadback，5项明确缺新preservation模块，非collect/依赖失败。source/runtime inputs前后SHA均保持。原report的containerRemoved=false是载体只匹配大写“No such”而Docker实际返回小写“no such object”；随后精确同名docker inspect实际exit1/[]/no such object，确认容器已删除，另存cleanup-observation，不改原report。载体仅修大小写识别，产品/冻结测试原样，允许进入最小GREEN。


GREEN候选r1实际9PASS/2FAIL，exit1、0error/skip、输入保持/容器删除。正向在ctx构造前因新owner策略仍复用旧预约而RESTORE_RESOURCE_RESERVATION_CHANGED，不是出版失败；已仅为新fixture创建独立operations/host/预约，保留旧预约字节。非法hold link原被FormalSnapshotError拒绝，正式入口增加明确PRESERVATION_HOLD_FILE_INVALID，不宽化底层guard。

候选r2实际10PASS/1FAIL，exit1、0error/skip、pytest61.356秒/outer123.766秒、输入保持/容器删除。正向已完成真实capture、strict Publisher.stream，进入完整SMB verify后PRESERVATION_DEADLINE。原capture.workSeconds60进一步收紧policy90，保留原超时证据；不能记作GREEN。父批准仅完整出版fixture显式capture180秒、policy180秒、ctx240秒，普通FULL三生命周期和全部生产默认预算保持。依据是r2已在60秒完成捕获/复制并进入完整读回，新完整阶段需独立读回全部载荷、binder和sidecar证明；新增有界timing按capture/copy/fullreadback记录真实阶段耗时于新r3私有原日志，不因超时关闭guard。预算仍同ctx对象/原绝对截止且capture进一步收紧，不新增Budget续时。

候选r3实际10PASS/1FAIL，pytest74.240秒/outer100.672秒，输入保持/容器删除；timing捕获33.437s、复制13.858s、完整读回13.237s。已真实完成完整SMB载荷读回，正式binder拒绝BACKUP_INTERFACE_BINDING_INVALID；定位新出版写入误用了capture journal的newline canonical，而RepositoryManifest正式合同要求repository canonical无尾newline。仅新模块写入改用原repository canonical+O_EXCL/NOFOLLOW/0600/fsync，普通capture/原publisher/binder原算法不改。

候选r4实际10PASS/1FAIL，pytest77.994秒/outer113.172秒，输入保持/容器删除；timing捕获35.356s、复制15.103s、完整读回13.186s。manifest已过正式binder，但source LIGHT的reference inventory明确complete=false，binder拒绝不完整材料；这是测试入口误用LIGHT证据，不能记为SAFE整体业务失败。父批准最小实际SAFE候选接缝：唯一隔离载体调用原standard_sources/safe_fixes，预加载原样formal_capture_semantics.py，测试核实际路径/原字节SHA和MinimalSemantic真实继承；其余MAIN源组件路径/SHA明确记录。该组合只证明新增MAIN材料核心与认证SAFE语义组件，不代表STANDARD封包/五transform/五保持点全部接线。原LIGHT、complete、binder不改。

BDD4边界澄清：2a仅实现preservation_holds函数及本次出版消费者，普通Catalog不枚举专用preservations目录；实际retention.plan/delete尚未消费新hold，留2b明确接线，不称完整retention门禁已完成。2a完整正向未PASS前仍in_progress。

候选r5真实10PASS/1FAIL、pytest4.801秒/outer23.140秒，输入保持/容器删除。实际SAFE语义组件路径/SHA已核，完整继承正确；失败是原有限S3协议fixture未实现认证SAFE调用的三种absent_configuration只读观测。仅新fixture按既有正式404/errorCode/rawSha/bytes合同补齐lifecycle/replication/encryption有限响应，未修改生产/SAFE语义/complete/binder。

首捕获前准入补充BDD（先RED）：Given同真实ctx/flock/预约、业务服务仍运行；When readback schema错、credential目标错、library字节漂移、认证未证明、目的设备明显无空间；Then TargetPreservation.prepare拒绝，Docker动作集保持、backend/frontend/MinIO仍运行且无archive-proof。现有MainTargetCapture.prepare已核当前服务/镜像/配置/原资源预约、capture工具原件、capture工作区maxWrittenBytes+reserve和原data恢复预算同device合并，但尚未核出版SMB和归档目的设备预算；不能把现有晚_publish门禁说成prepare完成。最小修正拟直接复用严格PreservationReadback构造/关闭实际新认证会话，在初始prepare建立本地publication根后、返回给调用者停写前完成；记录root可写独占probe与repo/readback/capture/data按设备的最大预算合并，出版时实际累积容量复核保留。新五项失败测试先冻结，不修改普通FULL/default LIGHT。

admission-red-r1真实16项10PASS/6FAIL，pytest38.26秒/outer63.219秒，输入保持/容器删除。五新增prepare全部DID NOT RAISE，是真实准入RED。正向已过SAFE严格语义capture阶段，在OBJECT_RECHECK处发现认证SAFE SemanticCapture.verify_endpoint旧签名不接受阶段1正式process_observer；不是忽略参数的理由。最小正式构造边界为该方法的1行keyword-only签名+7行原正式_bounded_process分支，默认原subprocess.run及SAFE complete/capture/finalize不变；已报父审纯候选transform边界，当前STANDARD实际交付仍HOLD。

父批准该精确纯候选接缝：AST只选唯一SemanticCapture.verify_endpoint节点，精确原方法字节只出现一次；只搬移阶段1已实际验证的正式observer方法，输出规范化完整原/后方法SHA，不覆盖整份SAFE源码，SAFE capture/finalize严格原字节。真实Popen/observer账本不替代。正式standard_fixes具名transform与双包交付仍待办。

仓库锁补充BDD（先RED）：Given目标真实flock/ctx同时有效；When另一真实Python进程持有原write.lock byte0、recovery-read-guard.json存在、write-unknown.json存在，或prepare后原lock文件身份被替换；Then prepare/check拒绝且无停写/无hold-intent（前三种），不能以目标flock代替仓库锁。复用原repository_retention.RepositoryLock(config,context._request)，不改其旧算法；configuration.current只指无仓库锁base guard，publication.check再核实际lock.check，禁止递归。仅在取得同ctx持有的原仓库锁并完成SMB/容量准入后，才提前独占写原hold-intent证明目的目录可写；同锁持到close，失锁关闭仍释放自身fd/local-owner并保留原错误。原context REPLACING不改READY，hold不是stage权限。

lock-red-r1实际20项11PASS/9FAIL，pytest139.43秒/outer182.844秒，0error/skip、源/副本保持、容器删除。完整真实出版/严格全读回/binder/专用point/terminal/proof/hold首次PASS；timing43.375/17.984/14.076秒。9FAIL仅准入5+仓库锁4，精确预期RED。SAFE方法原7b591ab228449f558e8321d0460136cdf3782e5b01a7a9688c909dbb803dc3c1/后1faa99c011eb7599b5716bfd1bdb4bb9018cb08a6faba9d9133310a506552c8e。

新增本地准入原件MainTargetPreservationResourceAdmission/v1精确字段：schemaVersion,operationId,devices,admitted,observedAt；devices每项device/requiredBytes/freeBytes。以实际设备合并原恢复diskBytesByPath、capture.maximum+reserve、policy.maxArchiveBytes、maxReadbackRecordBytes，每设备另保留minimumFreeBytes；真实observe_resources/shutil原容量观测，prepare先准入且出版再按实际字节复核。原RepositoryLock先于MainTargetCapture.prepare取得，同目标锁/ctx持有，configuration.current指base guard；失败关闭本地fd/会话而保留原件，不自动再捕获。

admission-lock-green-r1实际20PASS/0FAIL/ERROR/SKIP、outer177.328秒，exit0，源/副本保持/容器删除。包含完整真实出版和五准入、四原锁，未进入2b。

父批准最后三个2a闭合BDD（先RED，不扩范围）：(1) 完整真实出版后替换同内容payload inode或增加未登记archive成员，持续publication.check必须拒绝；只核SHA不足，复用原ArchivePathGuard对payload身份与完整目录集合持有，不新造watch算法。(2) 新认证连接构造因auth失败时只清自身私有cache，不遗留session，不碰其它连接。(3) 真实session._fail以clientCleanupUncertain固定unknown后，外层publication failure不能降回known；此为明确负向fault injection，不声称实际未reap子进程或伪造成功材料。现测试22场景，两种archive漂移各走同完整真实正向，其他原断言保持。后续只最小修正及一次普通FULL3生命周期/默认方法逐字/有限仓库回归，停止追加假设范围并冻结。

closure-red-r1真实22项18PASS/4FAIL、pytest258.59秒/outer287.547秒，0error/skip、源/副本保持/容器删除。四失败精确为三个闭合边界（archive同内容inode/额外成员各1、auth私有cache未清、session已unknown但publication错误false）；两条完整出版均先完成真实proof/hold才触发漂移断言，非提前fixture失败。最小修正：原ArchivePathGuard对复制后payload和archive全目录持有，sidecar写完后再封完整成员；strict新类构造失败关闭自身cache、保留主错误及cleanupUnknown；失败summary仅OR已有error/client/session/native unknown，不写成功终态。

closure-green-r1真实22PASS/0FAIL/ERROR/SKIP、outer291.875秒，exit0、源/副本保持/容器删除。代码与测试随后冻结。普通源FULL/仓库有限回归r1选中11项实际5PASS/6FAIL：原FULL成功/导出失败/来源恢复失败3项全PASS；root identity旧8项因载体误载LIGHT MinimumConfiguration.current而2PASS/6FAIL（与父先前r8相同入口差异），保留原件，不能标为2a产品故障或伪GREEN。仅对这8项按r9真实safe_fixes预加载认证repository_minimal/repository_records，逐实际路径/SHA核验，原测试断言不改、FULL3和新22不重跑。

## 2a最终有限回归、冻结与未接点（2026-11-10）

REGRESSION safe-r2原session17870实际exit0：8PASS/0FAIL/ERROR/SKIP，outer33.797秒，源/运行内输入SHA均保持、任务容器removed=true。真实认证safe_fixes输出的repository_minimal/repository_records已按实际__file__/SHA预加载；原八项root identity断言未修改。原regression-r1 session58141的5PASS/6FAIL保留，其中普通FULL成功、真实dump失败、来源恢复失败三生命周期均PASS；错入口的旧六失败不冒称产品GREEN。最终证据分别为新22、同一r1中的FULL3、r2的SAFE8，未重跑已通过项，亦不称33同轮PASS。raw/JUnit/快照完整pins见三份正式报告及freeze-r1。

默认入口核验：相对Git基线2e1e43fdde9f632e404df639eaac95ba83a866f2，repository_native_readback的relative_name及完整SmbReadback类原始源段逐字相同；repository_minimal全部19个原顶层定义在仅LF/CRLF归一化后逐字相同（当前工作区CRLF而Git blob LF，不能称原raw字节全等）。没有改变原LIGHT方法或普通publish算法；只新增显式材料入口。14+11阶段1、3+1阶段2a所有Python实字节compile静态exit0，无BOM；此静态结论不冒称产品测试。

实际调用覆盖：prepare先于目标停写完成typed原上下文/原capture配置准入、真实仓库字节锁、严格SMB schema/凭据/library/auth及设备合并容量准入，并在同锁写唯一hold-intent；正向经真实材料核心、Publisher.stream全部载荷复制、strict SMB完整读回、原binder、专用point/terminal/archive-proof/durable hold及末尾身份/成员集核验。外部Docker/SQL/Redis/S3/SMB仅有限本地协议，不是现场业务恢复或真实SMB写入证明。

必须保留的2b接线项（未实现，不可宣称目标可覆盖）：

- TargetPreservation.close当前由显式调用者负责；现ctx.close只关闭target_capture。2b必须把同一publication登记成同ctx终态资源，成功/失败均关闭仓库lock与leases，不能漏fd，不删除/释放durable hold。
- preservation_holds只被2a出版代码消费；实际retention.plan/delete尚未接线，专用preservations不被普通Catalog枚举，也尚非Spug可选择保留点。
- validate_archive当前只生成同live-context的typed归档验证结果；handoff/stage/首次clear/producer结果和历史闭包尚未接，archive-proof不授clear。stage以后绝不可用PREPARATION view继续派命令，须交新RESTORE native；首次clear必须独立复核原proof与合法新generation。
- 原RepositoryLock没有readGuard owner例外；来源repo已有readGuard时须正式配置独立保全目的root/policy，禁止改锁或伪例外。
- 完整SAFE五具名transform/五采集保持点、新成员及双包构造仍HOLD；本轮只验证已审纯候选唯一verify_endpoint observer接缝，认证capture/finalize原字节保持。后续包须独立新协议动态绑定真实manifest，不能把新成员套进已冻结147/146、current summary147或acceptance revision r7旧身份，不改旧SHA/断言。
- 58/59 capture及保全policy登记、实际安装/服务器/SMB/覆盖均未执行；原失败376与UNKNOWN不得重派。2b在父提交本冻结实现后再开始，不在冻结源中提前接线。

最终交付清单及每文件rawSHA：target-preservation-2a-freeze-r1.json。该清单区分第一阶段既有14产品/11测试/2文档与本阶段3产品/1测试/设计和TDD；无其它agent文件、无构建发布、无真实业务写入、无提交或清理。
