# 154→154实际载体接线

## Current Status

ready_for_closeout。本子项正式接线、可提交测试与离线载体已完成；待父精确提交及真实安装验收。继承released-main-installation-continuation-plan.md；不修改旧载体、product、current_installation、UI、custody或服务器。产品c2bc8b8正式包及真实两节点producer PASS已核，实际plan为PLANNED_NOT_INSTALLED。

## 目标与设计约束检查

- 目标：完整b10真实三host前代接c2bc8b8，复用既有154→154 fixed review/v3、candidate/activation v3和complete selection/v2，不建立新平台或复制validator。
- 是否引入fallback/降级/吞异常：否。旧输入变更只允许明确路径+SHA匹配的原始snapshot验证；任意未知漂移拒绝。producer未PASS即阻断。
- 是否从根因和长期维护角度解决：是。三个host都从完整prior.selection取真实activation；154旧包保全171，新写159。原clearance packet绑定其历史controller/owner，不能冒充当前b10。
- 是否存在临时补丁或绕过：否。不重写旧packet或历史输入pin，不把保全snapshot原路径伪造为当前路径；snapshot关系显式加入新planning原件。

## 经验门禁

Trigger：已完整三host安装的单控制成员后继。Preflight check：前代完整报告/selection及所有原输入或精确历史snapshot；真实STANDARD包和两节点producer。Blocker：未知pin漂移、非唯一native差异、无实际producer成功。Verification：纯本机BDD RED/GREEN、所有host三阶段离线compile/render，旧载体SHA不变。Forbidden action：SSH、提前制造PASS、修改旧报告/packet、复用更早58/59前代。Evidence：专属测试、planning/render原件及freeze。

## BDD

- Given完整b10前代及受审154同集合新包，When三host按本轮真实selection构造，Then fixed review闭合、159writes/171retained，载体三个阶段可编译且runtime subset等于正式函数。
- Given旧reader/UI原件已保全，When验证历史inputPin，Then只接受明确路径、原size、原SHA完全匹配的snapshot，当前源另外钉住；未知漂移拒绝。
- Given58旧b10已可用且原381历史clearance仍保留，When渲染，Thenbefore AVAILABLE，真实FAILED retry gate和55proof继续，原packet只匹配历史owner/controller，不改其内容。
- Givenproducer不存在/FAIL/其它package或计数，Whenplan，Then拒绝，不生成实际成功计划。

## 里程碑

1. 检查直接pin阻断及旧carrier依赖。
2. 独立新plan/run最小接线，先离线RED。
3. 离线GREEN、compile/render与旧字节验证后交父运行；不远端。

## 必要AVAILABLE验收关系

实际完整b10的58 native已有FAILED_RETAINED_RETRY_ADMITTED且API只对source57可选；旧verifier仅允许unavailable→available这一轮，不能承接已经可用的下一次组件升级。父已批准仅对新固定154→154 profile补此关系：正式loader从已完整验证的前代wrapper保存原native，当前native before/after必须全文等于此前代native；host58、source57、154→154、AVAILABLE明确同时成立；before/after API均只允许同授权source，retainedFailureAdmission/context保持None。默认及旧unavailable全部原判定保持，不伪造历史packet/controller。

BDD：Given已完整认证58前代的retry native，When固定单成员154→154后继仍为AVAILABLE，Then原FAILED/clearance/授权source/point/target全部相同且source58/59明确不可选；缺前代证据、任何native漂移、旧153/错误host/任何source越权均拒绝。先独立RED再实现；旧87063B/a1385049版本另存snapshot。

## RED → GREEN → REGRESSION

- AVAILABLE RED：新13节点12 FAIL/1 PASS，3.09s；缺正式predecessor_retry_native参数，原默认拒绝继续PASS。原输出released-retry-available-red-r1.xml保持。
- AVAILABLE GREEN：同13节点13 PASS/0 skip，2.73s；错误host/source/native/缺前代/旧count/旧schema/未授权API/context/admission全部拒绝。
- REGRESSION：原partial_native+successor_repeat共97 PASS/0 skip，30.27s；旧unavailable、READY及历史链不变。固定154→154原20节点再次20 PASS/0 skip，43.71s。
- 可提交测试迁移：scripts/tests/test_main_program_target_control_released_successor.py与test_main_program_target_control_released_available.py，无私密原件/固定电脑路径；合计33 PASS/0 skip，46.38s，released-main-portable-green-r1.xml。
- 载体RED：完整b10前代测试10节点2 FAIL/8 PASS，2.21s；旧actual_carrier对58/59错误取partial前代，无这两个host。GREEN修为三host全取完整prior.selection，10 PASS。
- 实际首render失败ORIGINAL_HTTP_SHAPE：b10旧carrier已含return validate_http_result(result)，原首次升级renderer仅接受return result。新载体明确只接受已验证b10这一形式，未知形状拒绝；旧render失败及r1plan原件保留，不SSH、不重写。
- 扩展compile测试green-r2为3 FAIL/10 PASS：失败来自测试误查base64封装中常量的明文，render已成功。改成核实际载入subset.PACKAGE_SAME_154_PROFILES等于正式常量；green-r3共13 PASS/0 skip，44.57s，涵盖三host×STAGE/PREPARE/ACTIVATE全部render+compile、runtime subset与正式函数逐值相等。
- PowerShell inline迁移命令曾在parser阶段失败，未写文件；改独立UTF-8 Python迁移后读回成功。无业务操作。

## 最终实际输入、保全与交接

- c2bc8b8官方STANDARD878017B SHA494d08e209e9588ade2ff2978cdd8ee9290853b2f46958adb41808441f8c178f，154成员同集合仅control/recovery_control_smallapp_native.py变化；producer2/0/0/0实际PASS后才生成plan。
- r2 planning：PRIVATE/released-main-successor-c2bc8b8-planning-r2.private.json，508086B SHAb9e71d35a2bd3257abfed23a7eae6443d925a3fba493289dfab9da7d4da5e35a。3host各159新写、171旧保全。原r1 planning保持原内容，不作为新执行输入。
- 原b10完整报告95,544,613B/1cb738c8…不改，原selection2539B/1416ba84…不改；1716历史inputs通过明确旧reader snapshot关系读取。旧83043B/803bfbd0…、84553B/d9639cdb…及87063B/a1385049…successor原件均独占保全；旧UI snapshot保持，当前UI另钉父已冻结32892B/fbb8f6ae…。
- 58历史clearance/55proof及extras继续逐pin保全；历史packet只绑定历史b9 controller/owner及原381，当前b10准入从已验activation wrapper得出。before API明确AVAILABLE、retainedFailureAdmission=None；source57可选、58/59明确不可选，native before==after==已验前代native。
- 新载体只在独立命名空间摘取精确钉住旧renderer/main/bootstrap，受审编辑均有唯一文本断言，原模块全局/旧载体字节未改。原physical lock、no_workers、保护业务、三阶段、原生门禁及1200s远端超时语义保持。
- PRIVATE/released-main-carrier-final-freeze-r1.private.json记录最终源/脚本/测试输出/9render pins及后续命令；本子项不SSH、不安装、不提交，不声称业务恢复成功。父的verify-released-main-successor-r1.py接口已只读核对兼容：新P.load_planning、common review、REPEAT/v2及唯一fresh正式loader，无新loader平台。
