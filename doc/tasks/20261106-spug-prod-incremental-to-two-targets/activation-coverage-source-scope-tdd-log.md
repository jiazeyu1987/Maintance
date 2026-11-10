# 历史 coverage 产品源码读取边界修复

## Current Status

`ready_for_parent_review`。父已审实际原blob/checkouts双字节合同，限定实现与必要验证完成：新14项、旧132项全部PASS，零失败/错误/跳过，输入前后保持。实现、专属测试与本日志已冻结，未提交；父负责独立审查及I1真实准入重验。前一CIFS prepare r3已由父真实执行：1项PASS，22.076秒；本阶段不修改其冻结载体、结果或hold。

## 目标与里程碑

1. 只读核`validate_generation_coverage`当前local proof与紧邻Linux source证据的物理来源差异；确认原build记录、control generation及冻结checkout中的原产品bytes/SHA。
2. 设计明确已提交build产品源码与TASK原件两种scope，不引入当前工作区fallback、不回写旧pin、不改全局历史读取模式。
3. 父审后新增真实文件RED：开发副本漂移但原build正确、原build篡改/缺失、路径越界、不得借开发副本兜底；再最小实现及必要旧相关回归。
4. 冻结源码、测试、实际输出与SHA给父；不服务器/Docker/HTTP/构建/安装/提交。

## 经验门禁

- Trigger：历史控制代次coverage读取产品源码误落开发workspace，合法开发修改导致旧已提交证据失败。Preflight check：原不可变build/coverage及实际冻结checkout的完整pin；区分产品、任务日志/测试原件及当前reader。Blocker：原件缺失、提交身份未知、路径越界、原摘要不符、fixture前置失败。Verification：真实文件读取RED→GREEN、完整原reader验证及有意义的负例；所有旧原件前后保持。Forbidden action：禁止改旧校验值、从当前workspace兜底、覆盖原checkout或旧失败、用mock成功替代reader。Evidence：父保留的原I1 preflight失败及本子日志逐阶段实际结果。
- 依据`docs/experience-index.md`命中构建输入隔离、历史接管/不可伪造证据与Windows载体前提门禁；本轮只读本机/有限单测，不执行真实E2E或服务器高风险动作。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，明确产品原构建输入与任务原件的职责边界。
- 是否存在临时补丁或绕过：否；不改旧合同数据或全局reader模式。

## BDD 初稿

- Given 旧coverage绑定的已提交build原件正确而当前开发副本已合法变化，When读取历史产品证据，Then从原build checkout读原字节并通过原摘要；任务原件仍读TASK。
- Given 原build产品丢失或被改动但开发副本恰好匹配旧SHA，When读取历史产品证据，Then明确拒绝，不回退开发副本。
- Given 产品或任务相对路径越界/链接别名，When解析证据scope，Then首读前拒绝，不读取scope外文件。
- Given 原TASK测试/日志被篡改，When读取历史证据，Then继续按原pin拒绝，不能把它重定向build来掩盖。

## 只读事实与设计审查

原`release-build-45dd7dc.json`固定checkout为PRIVATE/release-45dd7dc，targetCommit=`45dd7dc65409c87fe856584b85873ea96c0b830e`；真实`git rev-parse HEAD`一致、`git status --porcelain --untracked-files=all`为空。

同一产品`backend/src/main/resources/recovery_control_restore_catalogue.py`有两个不同但各自明确的原生字节事实：

- 旧local proof绑定20770B/SHA`d6dfd4701a5a6343af71329167b1167952b3328b4a52568e9ff21ae060c84ab9`。实际`git -C <原checkout> show <原commit>:<精确path>` exit0，原blob正好是此长度/完整SHA。
- checkout原文件21152B/SHA`3de7bcca9e72ad7c94b670f470924ccb92ba123553791f430da6c28906ad7e9d`，真实382个CRLF；这是原Linux `sourcePins`绑定的字节。原`catalogue-linux-input-r2.tar`2293760B/SHA`964a04dad8d4438adefcaa98f89c440ac10a7999c38b4c4036fa2b7db2b0090f`中的`repo/<精确path>`同样21152B/3de7bcca。此只读比较证明来源关系，不授权运行时归一换行。
- 当前开发副本20980B/SHA`0ad04cef8c57135b8207f416eff802f0bd6b7dbc0e23493dbac1e26965ba56ec`。local proof中的11个TASK原测试/日志目前全部完整bytes/SHA匹配。
- 原45/r6 generation2561B/SHA`2e29dd21044f2d7c44ba3a6800140ed225dec822b3e80944e4a84103b13b2b29`、coverage23187B/SHA`c385a5fac8a0a76f5e0c5164a49d8c2eed9b2c78bfdce9467cfa01a686495357`精确绑定该build；当前b5/r7 generation仍只消费这些历史原件，不能改其原pin。

父已据该事实批准最小实现方向：v1的local proof产品只读同commit Git blob原字节；产品路径必须实际存在于原checkout，且包含在原Linux sourcePins中并匹配其原SHA。TASK测试/日志继续原TASK物理路径。既有clean HEAD、checkout及双包验证和结束physicalPins复核保持。v2/profile分派不改。

## 精确实现与验证合同

仅在activation内增加有限产品证据reader及共同相对路径检查；不新schema/全局mapping。产品reader返回原raw、真实checkout物理pin与Git命令来源证明（sourceCommit、相对path、原blob bytes/SHA、实际exit0/timeout=false、stdout/stderr摘要）。Git读取先查固定blob大小并限64MiB，再读取同对象完整raw核原local proof；不做LF/CRLF转换、工作区fallback或旧摘要重写。Git非零/超时保留原异常和partial stdout/stderr，不伪造成功。

本轮有限RED先覆盖：真实临时Git中LF blob/CRLF checkout与合法漂移的独立开发副本；本地blob预期篡改；checkout篡改和缺失（即使开发副本匹配仍拒）；缺Linux绑定；原commit无该blob（即使checkout现有同名文件仍拒）；6种路径越界/别名；直接实际旧coverage完整reader。临时Git只用于协议单元，不是发布worktree或业务备份。原blob正确性必须由真正Git子进程证明，不mock成功validator。必要回归为既有v4 coverage/activation及证据pin相关用例。

## RED 执行

第一轮 PRIVATE/activation-coverage-source-red-r1 实际exit1，2 failed/12 setup errors/0 skip。实际原coverage明确复现line503 `MAIN_ACTIVATION_GENERATION_EVIDENCE_PIN_CHANGED`；TASK隔离负例仍被错误开发路径提前阻断。12个临时Git夹具在checkout-index后索引stat尚未重录，`git diff`无内容差异而status报M；这12个不计产品RED。夹具补实际`git add -- <固定path>`刷新自身索引并先核`git diff --cached --exit-code`为空，仍严格要求clean status和原Git blob raw相等；不改产品或放宽断言。原日志、JUnit、命令及native exit全部保留。

精确RED：PRIVATE/activation-coverage-source-red-r2实际exit1，14 failed /0 errors /0 skipped，21.79秒。12个真实Git/文件场景到达缺失`generation_product_source`；实际原coverage仍在line503原SHA门禁失败；TASK负例也精确受错误产品物理来源阻断。所有夹具前置已通过，未改任何生产代码。现在依据已审范围进入最小GREEN。

## GREEN / REGRESSION 与冻结

最小实现只改`main_program_control_activation.py`（50行新增/6行删除）：`generation_source_path`明确规范相对路径及实际scope；`generation_product_source`在已存在且匹配Linux sourcePins的checkout文件基础上，读取明确commit:path的真实Git blob原字节，限64MiB并核原local proof完整bytes/SHA。`GIT_NO_REPLACE_OBJECTS=1`禁止替换对象影响原commit身份。Git原非零/超时异常不吞；成功来源证明增加`committedSourceEvidence`，保存两个原命令、exit0/timeout=false及stdout/stderr长度/SHA、commit/path/blob pin和真实checkout pin。既有HEAD/clean、Linux所有源SHA、两代双包全成员/编译、原461证明、最后物理pins复核继续执行；v2/profile分派与原记录不改。

- GREEN命令：`python -B -X utf8 -m pytest <TASK>/test_main_program_activation_coverage_source_scope.py -q --tb=short -p no:cacheprovider --junitxml <PRIVATE>/activation-coverage-source-green-r1/result.xml`。实际14 PASS /0 failure /0 error /0 skip，65.68秒，nativeexit0，输入保持。包含实际完整历史coverage及两代双包读取，不使用成功validator替身。
- REGRESSION同一解释器与参数，文件为`test_main_program_control_activation.py`（24）、`test_main_program_control_generation_activation.py`（59）、`test_main_program_activation_evidence_pins.py`（13）、`test_main_program_control_generation.py`（36）。实际132 PASS /0 failure /0 error /0 skip，63.53秒，nativeexit0，输入保持。未重跑无变化产品包/服务器测试。
- `git diff --check -- <TASK>/main_program_control_activation.py`实际exit0。未Docker、SSH、HTTP、构建、业务备份恢复、安装或提交；未修改任何旧报告、Git blob、checkout原件或原失败。

固定解释器：`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`。本机依赖为PRIVATE/test-dependencies，pytest第三方自动插件禁用；真实完整命令、native状态和输入SHA在各阶段native.json；原stdout/stderr/JUnit均保留。

| 原件 | bytes | SHA256 |
| --- | ---: | --- |
| activation-coverage-source-red-r2/native.json | 605 | 1e773a7b306f40619d623fd646731cd2e3fdc375a341b956448fd6053462fbb4 |
| activation-coverage-source-red-r2/stdout.log | 12397 | 10011a462a2e2810d04df01d974c43726f63b5333420e52d251841382bc49ce2 |
| activation-coverage-source-red-r2/result.xml | 13530 | c102f3b6a8bdbf031a57fe8d5059e4a38e6248e66d433c895b6691619b44653a |
| activation-coverage-source-green-r1/native.json | 1011 | ed3f72798b1d608a3c5def53c3f39a08f233e3aed3862944ea4df5391909c354 |
| activation-coverage-source-green-r1/stdout.log | 249 | fe7083e498d1d0ef9b0c0da40d735a1a9a5847f84d7930ca8fb057aa4ac9cc46 |
| activation-coverage-source-green-r1/result.xml | 3443 | 18b36e6572d124407c58a91045fc37082bc3571fd5631fed505acebe4238a18d |
| activation-coverage-source-regression-r1/native.json | 1877 | 1376bed1a7ed0616a17e9d9aaa66821f38a590a19b61cefefece8ce378272bdd |
| activation-coverage-source-regression-r1/stdout.log | 336 | 251009ec1f81d866796bb795ffd9127c5c8b155226e421422201bb781a24da17 |
| activation-coverage-source-regression-r1/result.xml | 28834 | 57a91ffc4c160d1c65c165e1ae990c34c878db28db089b1e1bc52d4c96120e14 |

以上三个stderr.log均0B/SHA`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。

冻结实现：`main_program_control_activation.py`124365B/SHA`33429497d855ff5547ff6d82167d79016dcd932b980d85f8e5c2d467d522962d`；新测试`test_main_program_activation_coverage_source_scope.py`7816B/SHA`3ec52c5d0b2d27040efc19222ed23bc8556c3a98c2621a1f008d264f553e49d1`。父真实I1 preflight重验仍是后续独立阶段，不以本机146 PASS代替实际UI验收。
