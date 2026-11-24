# 测试服发布验收
版本2026-11-24-15-38-40，应用21f7528；JOB-dcd994c924 succeeded，OP-8bf34a876874b7a604f6 succeeded/stopped。manifest、IMAGE_TAG、双镜像、UP、HTTP200及正常开放均通过。三阶段当前数据库契约全部PASS。

Playwright真实芋道源码/admin登录、菜单进入排产工单页（接口code0，当前0行，不虚构有订单数据）、页面版本/提交/变更说明通过。打印助手18733运行时URL及真实票据认证iframe通过；未执行实际打印。

## 页面观察
两份脚本各6条观察全部保留：统计hm.baidu.com连接关闭对应请求/console共2条，属于非必要统计，菜单/版本/打印实测通过；外部头像ORB1条，用户身份与必要功能实际通过；事前只读拦截workbench/context及对应请求/console3条，该工作台初始化不在本轮页面范围，未据此声明工作台通过。以上逐项评估为非阻断，结论PASS_WITH_OBSERVATIONS；外部资源由应用维护。无未知异常或必要接口业务失败。

仅测试服构建发布及基础页面验收。原加入活跃订单真实业务基线阻塞保留，不宣称其通过；未执行mark-tested、promote-prod或promote-backup。

包manifest文件SHA与远端契约回执使用的规范JSON package_identity分别记录，已按实际算法交叉核对。SQL遵循已提交.gitattributes的CRLF规则，包内字节与manifest匹配；Git blob SHA另记，禁止混用。
