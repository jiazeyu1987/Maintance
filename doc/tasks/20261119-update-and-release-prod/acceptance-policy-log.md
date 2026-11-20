# 发布页面验收规则统一

## Current Status
ready_for_closeout

## 目标与范围
统一login-access与发布checklist对console错误的判定。仅修改登录规则和新增统一页面验收规则；主线程同步checklist和经验索引。不修改业务代码、认证自动化，不操作服务器。

## 里程碑与验证
- [x] 核对原规则冲突和适用边界。
- [x] 定义基础冒烟、逐项异常归因和三种判定状态。
- [x] 核对Given/When/Then场景决策表、交叉引用、UTF8和diff。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否，未知与必要功能失败仍阻断，异常完整留证。
- 是否从根因和长期维护角度解决：是，唯一规范入口，登录文档只引用。
- 是否存在临时补丁或绕过：否，不按域名/HTTP方法/错误文本设忽略名单。

## 经验门禁
- 发布验收绑定同包版本及实际目标，真实登录和页面操作，不以API-only或静态页面冒充。
- 全部console/pageerror/失败请求保留；观察通过必须给出逐项来源及必要功能不受影响的证据，未知立即阻断。
- 页面冒烟不替代IntRuoyi业务回归、版本/镜像/健康或来源同步证明。
- 凭据、token、请求正文和URL查询参数不进入公开记录；中文显式UTF8。

## BDD
- Given登录和必要页面全部真实通过且无异常，When判定，Then PASS。
- Given非关键外部请求失败且逐项证明必要功能不受影响，When判定，Then PASS_WITH_OBSERVATIONS并保留观察及范围。
- Given任一异常影响未知、必要请求失败或业务code非成功，When判定，Then BLOCKED。
- Given只读验证器主动阻断请求，When不能证明它对本次必要路径无影响，Then BLOCKED，不以主动拦截自动豁免。
- Given基础冒烟通过而Excel回归未执行，When汇报，Then仅声明冒烟结果，业务回归保持未执行。

## 执行
- 原规则冲突已确认：login-access原“console errors非零必须BLOCKED”与checklist观察通过存在不同判定。统一规则收敛为真实影响/完整证据判定，未知保持BLOCKED。
- 变更：docs/login-access.md引用统一规则；docs/release-page-acceptance.md记录基础范围、全部异常留证、5项观察准入条件、BLOCKED优先、9行Given/When/Then决策表、执行阶段与记录格式。现有认证脚本/人工备注的证据限度明确，不宣称自动化已经接入。
- 规则场景审查：无异常且必需检查齐全PASS；console为0但缺必要证据BLOCKED；业务code/必要资源失败BLOCKED；证据完整的非关键外部失败或事前只读拦截观察通过；仅域名/历史说明或未知影响BLOCKED；基础冒烟通过不改变未运行业务E2E。对应上文BDD逐项覆盖。
- GREEN: 显式UTF8无BOM读回、3份文件相对链接存在、6项门禁字段齐全、旧console数量硬判定已移除 -> PASS；git diff --check针对3份文件 -> exit0。
- 本项仅文档规则治理，未新增生产代码或形式化测试文件，不将文档审查记作真实E2E通过。未提交、安装或远端执行；checklist/experience-index同步、合并和工作区收尾由主线程负责。
