# 版本一致性与验收规则统一

## Current Status
completed

## 目标与范围
用户要求先处理发布版本一致性及验收规则统一。沿用20261119发布任务，仅修改本机维护仓正式代码、测试、文档并融合，不重新发布IntRuoyi应用。页面规则统一不自动追认旧验收；Excel业务实现归IntRuoyi。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。未知路径、错误影响、身份或文件漂移均拒绝。
- 是否从根因和长期维护角度解决：是。元数据收口独立于备份配置，统一入口和恢复尾部；页面规则采用唯一判定文档。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- 新工作区C:/SpugHandoff/release/maintenance-version-acceptance-20261120，分支codex/release-version-acceptance-20261120，起点1b3bd9537288770caf3210323b6e3dea814829c5；主区不测试，其他任务内容保留。
- 对齐前运行态/manifest镜像身份及公共操作锁必查，显式runtimeEnvironmentFile或既有备份来源environmentFile合同，冲突/缺失不推断。
- 原件0600、容器/包绑定intent、原值并发检查、原子更新/读回；失败保留同任务尾部，不能重派SQL或部署。页面未知影响及必要功能失败阻断，观察通过需逐项真实证据。
- 本轮无构建/服务器安装/部署命令。融合前只提交明确文件集；融合后回归，清理仅本轮工作区，原发布任务的旧工作区单独跟踪。

## BDD与TDD
- Given test/prod/backup目标无备份绑定但显式.env，When 正常双容器健康通过后结束发布，Then 检查镜像ID和RepoTags、对齐唯一IMAGE_TAG并保留原件，其他字节保持。
- Given 镜像/路径/原值/容器身份不符，When 对齐或续办，Then 失败且不伪造完成。
- Given 对齐后结果回执未写完，When 同身份尾部重试，Then 以完整intent和原件验证继续，不覆盖历史原件。
- Given 页面基础冒烟，When 评估所有异常，Then 必要功能/未知影响阻断，证据完整的非关键观察允许范围内通过；完整Excel回归另行说明。
- RED：新模块未存在；随后实际finish_reopen入口缺runtimeMetadata结果、对齐失败未阻断，2项测试真实失败。首次入口测试缺远端注入BACKUP_SOURCE_PROGRAM是夹具缺口，修复后再取上述RED，未把夹具错误当业务RED。
- GREEN：元数据11项及入口集成通过；首次128项回归2项旧夹具缺新增依赖，补明确模块边界后167项PASS。扩大既有关联回归221项PASS（其中source_binding_entry重复列一次，最终报告将使用去重模块命令）。
- RED：回执写入中断留下最终文件；改同目录临时文件fsync后原子替换，16项元数据及入口测试PASS。
- 复审发现测试服已开放元数据失败不能经旧原任务续办；继续补实际resume_test_tail入口场景，未宣称所有恢复路径已通过。

## 里程碑
- [x] 规则与入口核实，BDD和失败证据。
- [x] 三环境共同对齐及页面统一文档。
- [x] 续办实际入口、回归及独立审查。
- [x] 实现提交、融合后复验、本轮工作区删除、最终记录。

## 实施结果与验证
- 自动对齐独立于备份来源，正常双容器健康后对齐；元数据失败保留同包、前后端容器ID绑定尾部。测试服原任务续办新增严格正常开放分支，复用原包/恢复点/完整台账/原容器验证，不重放SQL或部署。同镜像替换容器、活跃worker、配置/台账漂移均拒绝。
- 页面三态判定已统一到docs/release-page-acceptance.md；规则审查覆盖9个BDD情形。文档不冒充自动页面采集或历史验收追认。
- REGRESSION: 隔离工作区ops/spug/release-center内运行以下命令，254 tests PASS、零跳过。首次附加模块名称test_resume_test_deployment_executor误写产生ImportError，未计为通过；rg确认真实入口test_test_tail_adapter后完整重跑通过。
```text
python -X utf8 -B -m unittest test_release_runtime_metadata test_runtime_metadata_entry test_source_binding_entry test_resume_test_tail test_test_tail_adapter test_intruoyi_runtime test_technical_verification test_direct_release test_source_runtime test_route_snapshot_handler test_stopped_origin_entry test_stopped_origin_recovery test_interruption test_origin_audit_closure test_candidate_history test_intruoyi_build test_gxp_release_mode test_stopped_source_mode test_intruoyi_flow -q
python -X utf8 -B scripts/tests/test_runtime_env_metadata.py -q
```
- 第二条命令从隔离工作区根目录执行，原独立工具5项PASS。实际Python为C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14/python.exe。
- 未构建应用、未安装运行中执行器、未操作服务器、未做新的真实页面或Excel导入验收；这些测试是本机单元/入口集成验证，Docker/SSH边界使用测试替身，不记真实E2E。
- 已产生新提交：实现363a6ca50baf484519939c559f4bceaeca2b4395，仅13个明确代码/测试/规则文件；中间记录aa653fa15b461e8800a20800faa18564c9ead5f8。提交前主区对应13路径干净且索引空，UTF8及规则相对链接/6项门禁字段检查PASS，git diff --check PASS。

## 最终收尾
- 两提交已fast-forward合回维护int_main，合并后核隔离工作区HEAD等于int_main，在同提交重新执行上述254+5项测试PASS，零跳过。未在主工作区构建或测试。
- 清理第一次因41个ignored Python字节码被正式工具拒绝；逐文件核路径在本轮worktree内、对应源码存在、Python magic及git ignored身份后记录摘要并仅删除这些生成物，未改清理门禁或删除未知内容。
- GREEN: 官方integration_worktree_cleanup.py -> PASS；commit=aa653fa，verifiedTrackedFiles=5223，gitRemovalExitCode=0，registeredAfter=false，physicalPathExists=false。本轮工作区已删除。外部回执C:/SpugHandoff/release/version-acceptance-20261120-cleanup-result.json，缓存清单同目录version-acceptance-20261120-cache-cleanup.json。
- 本轮未启动或改动运行控制台，无需恢复；现行执行器未安装本轮代码。下次安装前必须按checklist核各环境显式.env配置、新模块运输及实际入口，不能用本机回归宣称线上生效。
- 本子项completed；原发布任务其他4个旧工作区及历史页面证据的最终收尾仍单独跟踪，不由本次规则变更自动追认或清理。
