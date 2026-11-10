# MAIN 自动增量验收预检 TDD

## 范围与设计

只扩展本任务验收工具，产品来源/目标和控制配置不改。正式v4严格解析后，当前Spug十四资源、七配置与entry身份逐项核实；来源通过真实SSH只读核原MAIN五容器、147文件、全部语义健康、epoch/UUID/捕获范围、物理锁、无worker及恢复预约，最后请求正式原生自动计划。四存储角色逐一核容量，即使路径相同也保留各角色。READY沿当前已验证根和父点，不重做FULL。

## BDD / RED / GREEN / REGRESSION

- Given既有READY完整链，When新cycle I1预检，Then允许承接既有根和父点；verify沿原请求计划而不是已推进的新计划。
- Given身份/MAIN范围/健康/空闲/四容量缺口，When准备真实点击，Then无gate且不派发任何备份或恢复。
- RED: `python -m unittest test_main_program_ui_preflight`实际exit1，缺新模块；先写7个场景。
- GREEN: 最小实现后7 PASS。
- 真实只读r1（原会话99236 exit1）在容量角色检查拒绝：repo与archive同路径导致四角色字典合并为三；不是现场容量不足。未签发gate、无业务写入。失败记录main-program-ui-preflight-preview-r1-failure.json。
- RED: 新增容量角色精确负例，替换archive为other仍四项时原实现未拒绝，Missing expected exception，exit1。
- GREEN: 按角色保留测量/路径并要求精确四角色；8 PASS。所有源码和远端只读脚本编译PASS。
- 实际preview r2（原会话19409 exit0）严格v4、实时Spug身份/14资源/7配置、真实来源MAIN容器匹配、健康/锁/容量/原生READY计划全部PASS。源UUID与原373全备一致；373冻结证明885表。没有备份/恢复派发。
- 首次父回归误用unittest收集pytest文件且缺pytest依赖，exit1；不是产品失败，不计通过。
- REGRESSION: 使用既有private test-dependencies，`python -m pytest -q -p no:cacheprovider test_main_program_ui_preflight.py test_automatic_ui_preflight_git.py`原会话99282实际exit0，35 PASS、0skip、113.27秒。
- 父Node独立回归原会话工具终态exit0，9新+6旧=15 PASS、0skip、543.1738ms。子代理TDD原始失败/绿色另见automatic-main-cycle-ui-tdd.md。

这些单元合同不能替代实际浏览器备份/原生终态及恢复。实际UI预览/唯一提交另行记录。PRIVATE原始运行资料不提交凭据。
