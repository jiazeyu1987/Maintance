# 任务记录提交 helper 的阶段与范围修正

## Current Status
ready_for_review — 已纠正final对开发checkout的过严删除条件，37项专属合同通过；新验证见records-commit-helper-retention-regression.json，旧记录保持。没有任何Git写入或清理。

## 目标与里程碑
旧helper在import时读取packaged-frontend旧提交，并要求completed后才提交全部TASK文件，混淆验收记录与最终收口，且会自动纳入共享文档。本次建立明确、可复核的两阶段命令和逐文件pin清单。
- M1：先写Given/When/Then和失败测试，证明显式HEAD、阶段分离及精确清单缺陷。
- M2：最小修正commit_records.py；默认只准备，显式execute才允许Git写入；已有历史证据不可覆盖。
- M3：真实临时文件负向合同、命令行解析、语法和既有收尾合同回归；父任务审阅后自行使用，不在本轮执行提交。

## 预期验证
使用真实临时文件验证pin变更、路径越界、旧Nov4资产、重复清单、缺失融合/清理依据和错误状态的失败。测试为本机helper合同，不冒称真实提交、服务器验收或E2E。所有生产Git状态保持不变。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否；不从旧安装报告推断HEAD，清单与依据缺失即拒绝。
- 是否从根因和长期维护角度解决：是；阶段、显式输入、不可变回执与逐文件pins分开，防止未来新增构建提交再次使HEAD硬编码失效。
- 是否存在临时补丁或绕过：否；不改变任务完成条件，不用ready_for_closeout伪造completed，不绕主线dirty融合门禁。

## 经验门禁
- Trigger：实现验证通过后需要先提交验收记录，而融合/清理尚未结束。Preflight check：显式40位expected HEAD、真实分支和空index、精确文件pins、任务首个Current Status、语法与私密值扫描；final另外核实际祖先关系和融合/清理/稳定控制证据。Blocker：HEAD或文件漂移、非本任务文件、已有暂存、状态不符、证据缺失。Verification：准备前后HEAD/index/非选定改动不变，execute仅精确暂存且再次检查pins。Forbidden action：禁止glob全量暂存、git add -A、旧Nov4文件进入、静默降级阶段、覆写原证据、未授权Git写入。Evidence：本方案、专属测试/回归结果与将来由父任务实际生成的新准备回执。
- 现行worktree-memory第203—207行仍适用dirty主线；该helper不执行stash/融合/删除，不产生处理共享日志敏感历史的授权。

## BDD
- Given 输入当前b5或未来完整已提交HEAD；When acceptance准备；Then 不再读取旧packaged-frontend提交作为HEAD门禁，显式HEAD不匹配仍失败。
- Given task.md首个Current Status为ready_for_closeout，记录已通过本机检查；When acceptance准备；Then 可准备该阶段记录，不能写completed，不要求先清理worktree。
- Given 仅task.md写了completed但缺真实融合、10个临时发布build清理或稳定控制证据；When final准备；Then 必须失败；模式不能静默互换。
- Given manifest列出具体TASK文件及允许的共享文档pins；When任一文件漂移、越界、重复、删除或包含旧Nov4路径；Then 不暂存、不提交并报告不含秘密的错误码。
- Given默认命令或失败检查；When helper运行；Then 不产生Git写入；只有显式execute且全部门禁通过时才能进入原提交步骤。
- Given原准备/提交回执已存在；When重跑；Then wx拒绝覆盖，不修改旧证明。
- Given 10个临时发布build已删除、实际main融合/回归/并行保全齐全，而开发checkout按retained_with_preexisting_assets保留；When 实际路径/登记/HEAD、42项既有资产pins及本任务改动承接均核对；Then final允许继续，不要求删除开发checkout。
- Given 任一既有资产缺失/字节变化、保留路径不符、HEAD尚未合入main或本任务dirty尚未承接；When final检查；Then 明确失败，保留现有文件，不自动删除、暂存或提交。

## 开发checkout处置纠正
AGENTS强制收尾删除的是本任务临时发布worktree，当前10代build仍逐项核清理。原helper把该要求扩展到长期开发checkout，属于本helper过严，不能作为项目规定引用。原42项旧资产保持，不以它们和checkout仍存在为失败理由。
final独立证明明确disposition=retained_with_preexisting_assets，绑定原integration-pending-scope.json的42项资产pins；只读核实际保留路径/Git登记/HEAD已合入main。只检查本TASK和明确共享docs的dirty：已在main HEAD中，或字节完全等于本次final显式清单者已承接，其余阻塞。后一情形用于本次将提交的最终记录，避免提交后新增独占回执形成自引用循环；不把未知旧资产混入任务。

## 接口设计
`--mode acceptance|final --expected-head <40小写hex> --selection <本TASK清单> --receipt <本TASK新文件> [--finalization <本TASK最终证明>] [--execute]`。
selection为`TaskRecordSelection/v1`，mode/expectedHead必须与CLI一致，files每项path/bytes/sha256，必须含本TASK/task.md；不是自动扫描白名单。acceptance要求任务分支与ready_for_closeout；final要求int_main与completed并附固定字段的独立最终证明。准备回执以新文件独占创建；不改任务状态、不自动纳入新回执、不覆写records-verification.json。具体最终证明schema在实现和专属用法中冻结。

## 验证结果
- RED：19项首次测试失败，旧helper没有明确阶段、显式参数和逐文件pins接口；原输出records-commit-helper-red.txt保留。
- GREEN：首轮19项通过，不要求先写completed。
- RED补充：28项中搬迁副本定位、650路径分批检查2项失败；原输出records-commit-helper-red-r2.txt保留。
- 历史GREEN：TASK改为当前脚本实际位置；检查每批最多30路径，28项全部通过。覆盖真实临时文件漂移、旧Nov4/PRIVATE/重复/越界拒绝、独占回执和当时final合同；其中“保留开发checkout则失败”现已认定过严并由本轮新合同取代，不再作为正确行为。没有把合成单测fixture称为真实主机或融合验收。
- 真实只读负向CLI：当前工作区输入全0错误HEAD，明确HEAD_CHANGED_REVIEW_OWNED_SCOPE；index字节前后完全相同，没有创建回执或Git写入。
- finalization当前schema为v2，精确使用顺序见records-commit-helper-usage.md。原开发checkout和42项旧资产按明确保留处置；当前final尚缺真实main融合等证据，不因保留checkout本身失败，没有自动删除或自引用pin。
- RED补充：第30项范围测试发现旧非选定文件保护会读取全部无关文件内容（真实主线有9949 dirty路径），records-commit-helper-red-r3.txt保留。
- GREEN：非选定路径仅核Git路径集合和lstat身份/大小/mtime/ctime，不读无关内容；选定文件仍完整SHA。30项通过，实际文件修改仍能检出。该身份快照不冒称无关文件全文校验，最终融合字节保全仍由独立mergeVerificationPin证明。
- RED（本轮）：records-commit-helper-retention-original-rejection.json证明原完整v1本机fixture会仅因保留checkout返回DEVELOPMENT_WORKTREE_STILL_PRESENT；这不是项目显式要求。新增35项测试在旧实现11项失败，原输出records-commit-helper-retention-red.txt保留。
- GREEN（本轮）：v2明确retained_with_preexisting_assets，检查原路径/Git登记、42资产完整pins、HEAD已融合、本TASK/shared-doc dirty在main或本次final清单中承接；37项PASS。10代build仍必须删除，未改该清理门禁。Git观察依赖使用显式单元合同fixture，真实临时文件验证资产变更/缺失；不冒称真实融合。
