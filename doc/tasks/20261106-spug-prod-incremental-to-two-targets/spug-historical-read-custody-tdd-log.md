# Spug 历史原证明读取 TDD

## Current Status

ready_for_closeout。第一阶段实现/新合同验证已冻结，待父独立复核和提交；全任务及第二阶段尚未完成。父已批准 `spug-published-control-generation-acceptance-plan.md` 第一阶段及四个reader自身旧字节保留范围。父独立保存的 `PRIVATE/spug-historical-read-originals-20261110-r1/preservation.json` 是本轮只读输入；本分工不提取Git源码、不改该原件、不远端、不提交。

## BDD与里程碑

- Given 当前真实v4 selector、原完整v3/565及五attempt，When 明确custody消费原activation及各attempt具体reader原版本，Then 完整原历史闭合；不变更旧逻辑inputPins。
- Given 同一路径在不同attempt含不同SHA，When 校验，Then 按attempt及完整originalPin分别核，不按路径覆盖；已有custody冲突、未知源码、缺原字节或当前reader漂移均拒绝。
- Given 无historical参数，When 原入口读取，Then 原错误与合同保持；不能为了绿色放宽旧fixture。
- Given 只读历史验收，Then 原stage/program/native argv/exit/输出与终态逐值保持，全原件及当前源码前后SHA保持，transport不派发。

阶段：先新增实际文件RED；最小实现；新合同GREEN；必要旧回归并按真实原件漂移归因；冻结交父。第二阶段r7验收不在本轮实现。

## 设计约束检查与经验门禁

- fallback/降级/吞异常：否。根因与长期方案：是，历史逻辑身份与当前读取输入分开。临时绕过：否。
- Trigger/Preflight：按已审计划核精确五attempt与父保存原件；reader映射新增明确attempt字段，禁止同路径覆盖。
- Blocker：任何不关联原attempt、别名/硬链、未保留版本、映射冲突或业务原件漂移。
- Verification：真实临时文件负例、当前真实完整原历史、本机原参数回归；命令退出、零skip及前后pins分别记录。
- Forbidden action：不修改旧报告/selector/inputPins、不执行旧源码、不隐式发现或全局mapping、不执行服务器与配置写入。
- Evidence：父保存原件、前序宽回归失败、本日志及原生测试日志。

## RED r1

`python -B -X utf8 -m pytest <TASK>/test_main_program_spug_historical_custody.py -q --tb=short`：exit 1，1 passed / 27 errors / 0 skipped，4.77s。27 项均因正式模块 `main_program_spug_historical_custody` 尚未存在而报 ModuleNotFoundError；无参数旧入口拒绝源码漂移的场景已 PASS。实际日志：PRIVATE/spug-historical-custody-red-r1.log。之后最小实现单一显式载体和四 reader 的 keyword 参数；阶段原程序、命令、退出、输出比较不改。

## GREEN候选与加载身份RED

- 首次候选：27 PASS/1 FAIL（17.76s），实际transition build custody条目还含已验证的relativePath。helper只消费两pin合同，caller现明确投影原有已核条目的originalPin/preservedPin；不改原件或放宽已有build验证。原日志spug-historical-custody-green-r1.log保留。
- GREEN r2：28 PASS/0 skipped，exit 0，19.22s。完整真实历史入口已通过publication失败、c1已写前缀、依赖补齐、565转换和v3完整验收全部原生阶段，原件前后pin保持。日志spug-historical-custody-green-r2.log。
- BDD补充：Given 四个currentReaderPins正确但实际导入reader的__file__不同，Then 在消费历史前拒绝；同一原reader在另一attempt有映射不能替代本attempt映射。
- RED r2：两新增场景1 FAIL/1 PASS，28 deselected，0 skipped，exit 1，12.75s；失败为loaded-reader身份未抛错，日志spug-historical-custody-red-r2.log。随后仅追加固定四模块实际__file__精确核验，不动态载入任何旧源码。

## REGRESSION r1 与最终 GREEN

联合命令为 `python -B -X utf8 -m pytest <TASK>/test_main_program_spug_historical_custody.py <TASK>/test_main_program_spug_publication_continuation.py <TASK>/test_main_program_spug_publication_verify_only.py <TASK>/test_spug_runtime_dependency_completion.py <TASK>/test_main_program_spug_resource_transition.py <TASK>/test_main_program_installation_selection.py -q --tb=short --junitxml=<PRIVATE>/spug-historical-custody-regression-r1.xml`。PYTHONPATH固定PRIVATE/test-dependencies，PYTEST_DISABLE_PLUGIN_AUTOLOAD=1。

实际exit 1，183 PASS / 2 FAIL / 70 setup ERROR / 0 skipped，129.71s；全部实现与测试输入前后SHA保持。完整日志/命令/输入摘要/JUnit分别为PRIVATE/spug-historical-custody-regression-r1.log/json/xml。不得称为全回归PASS。

| 测试文件 | PASS | FAIL | setup ERROR |
| --- | ---: | ---: | ---: |
| 新historical_custody | 30 | 0 | 0 |
| publication_continuation | 55 | 2 | 0 |
| publication_verify_only | 6 | 0 | 26 |
| runtime_dependency_completion | 29 | 0 | 10 |
| resource_transition | 1 | 0 | 34 |
| installation_selection | 62 | 0 | 0 |

72个旧失败/前置错误全部是未传historical的真实旧入口抛 `MAIN_SPUG_ORIGINAL_BYTES_CHANGED`。保留旧测试/旧原件和严格错误；不修改旧expectation、不将新入口隐式接入发布或执行路径。

静态审查发现旧transition测试的baseline-reader协议仅收4个位置参数。BDD：Given 未传historical，Then 保持原4参数调用；只有显式上下文才增加keyword。新增真实协议边界RED r3为1 FAIL/30 deselected/0 skipped、exit 1、0.38s，具体TypeError unexpected keyword historical；不伪造历史成功。最小修复仅在 `_prepare` 有上下文时传该keyword。

最终GREEN r3：31 PASS/0 skipped、exit 0、30.65s，全部6个实现/测试文件前后SHA保持；PRIVATE/spug-historical-custody-green-r3.log/json。相对父独立保存的四reader，AST差异仅为continuation的prepare_value/load_failed_originals/validate_source_custody、dependency的validate_failed_continuation、verify_only的prepare_value/prepare_transition_verification/validate_publication_v4/load_completed_dependency_activation、transition的_prepare/transition_reference/load_completed_transition。原stage/program/native/transport函数均未变。最终源码冻结，不再扩大接口。

## 父复核用显式实际载体构造命令（本分工未执行）

下列Python正文由父使用固定Python `-B -X utf8` 运行；只创建一个新PRIVATE载体，O_EXCL拒覆盖。读取父已保存的原字节和当前真实报告，不提取Git、不执行旧源码、不访问远程。若正式输出已存在，必须停止核原因，不换名重试掩盖结果。

```python
from pathlib import Path
import json, sys
task = Path('C:/Users/D01021/.codex/worktrees/spug-restore-targets/Maintance/doc/tasks/20261106-spug-prod-incremental-to-two-targets')
private = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
sys.path.insert(0, str(task))
import main_program_spug_historical_custody as history
import main_program_spug_publication as publication
import main_program_installation_selection as contract
records = contract.Records(task)
selected = records.read(history.SELECTOR)
vi = records.pinned(selected['verificationInputsPin'])
base = records.pinned(vi['baseVerificationInputsPin'])
c1 = records.pinned(base['continuationInputsPin'])
dependency = records.pinned(base['dependencyActivationPin'])
wrapper = records.pinned(vi['resourceTransitionPin'])
transition = records.pinned(wrapper['transitionCorePin'])
rich_path = private / (selected['spugInstallationPin']['file'][:-5] + '.private.json')
rich = json.loads(publication.verify_bytes(publication.file_pin(rich_path)))
attempts = dict(publication=c1['originalAttemptPin'], continuation=base['continuationAttemptPin'],
    dependency=dependency['attemptPin'], resourceTransition=transition['attemptPin'], verification=rich['attemptPin'])
preserved_path = private / 'spug-historical-read-originals-20261110-r1/preservation.json'
preserved = json.loads(publication.verify_bytes(publication.file_pin(preserved_path)))
rows = []
for label, reference in attempts.items():
    attempt = json.loads(publication.verify_bytes(reference))
    for row in preserved['readers']:
        if row['originalPin'] in attempt['inputPins']:
            rows.append(dict(attempt=label, **row, currentPin=publication.file_pin(row['originalPin']['path'])))
value = dict(schemaVersion='MainProgramSpugHistoricalReadCustody/v1',
    selectionPin=records.references[history.SELECTOR], verificationInputsPin=selected['verificationInputsPin'],
    verificationCorePin=selected['spugInstallationPin'], resourceTransitionReferencePin=vi['resourceTransitionPin'],
    attemptPins=attempts, activationSource=preserved['activationSource'], readerCustodies=rows,
    currentReaderPins=[publication.file_pin(task / name) for name in (*history.READERS, 'main_program_spug_historical_custody.py')])
output = private / 'spug-historical-read-custody-45r6-parent-r1.private.json'
publication.exclusive_bytes(output, publication.canonical(value))
custody_pin = publication.file_pin(output)
result = history.load_historical_publication(task, private, custody_pin)
print(json.dumps(dict(custodyPin=custody_pin, status='HISTORY_READ_PASS',
    generationCommit=result['generation']['generation']['sourceCommit'], physicalInputCount=len(result['inputPins']))))
```
