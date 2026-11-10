# 真实 UI 浏览器模式

## Current Status

implemented_verified_locally；RED实际3FAIL/1PASS，最小实现后六文件56PASS/0skip。真实UI尚待。用户目标和既有真实UI授权保持；headed MAIN 两次原60秒导航超时，独立headless只读GET实际载入10.546秒但截图5秒超时，不能宣称模式必能解决。新增明确 `--browser-mode headed|headless` 是可重复的Playwright运行方式，默认保持此前MAIN headed/普通headless。原CJS先按旧SHA保留PRIVATE，旧attempt与收据不改。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；显式选择，不在失败后自动换模式，不延长时限或放宽检查。
- 是否从根因和长期维护角度解决：是；运行模式成为有记录的测试输入，便于区分浏览器呈现和服务响应。真实页面和应用流程保持。
- 是否存在临时补丁或绕过：否。

## 经验门禁、BDD 与验证

真实r7进入登录前响应等待发生45秒拒绝，而按钮click尚未返回；未及时附加promise拒绝处理导致Node在原catch/finally前退出，原native保留、无页面报告。新增有限缺陷修复：Given 响应等待先于click失败，When 45秒超时，Then 立即持有原error，click完成后仍抛原error进入失败报告，不吞错误、不延时、不登录重试。先真实拒绝Promise RED，再最小观察函数及旧合同回归；成功Response对象不复制或伪造。

Given 既有调用没有新参数，When 选择浏览器配置，Then MAIN仍headed/普通仍headless。Given 显式headless，When 从真实页面验收，Then 只改变Chrome启动/bringToFront条件，登录、身份、源包pins、15分钟准入、原receipt、唯一POST、终态与截图都保持。Given 非法或重复模式，When 解析参数，Then 在浏览器启动前拒绝，不默认为另一种。

先新增真实参数解析/模式函数合同并记录RED，再最小实现和现有UI合同回归；无浏览器/网络的合同不冒充真实E2E。真实验收必须新鲜准入，verify原operation，不使用--execute，不覆盖旧失败原件。里程碑：RED→GREEN/回归→新鲜preflight→真实UI终态；未通过项如实保留。
