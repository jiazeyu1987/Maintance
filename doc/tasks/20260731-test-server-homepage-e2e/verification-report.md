# 测试服首页只读 E2E 验证报告

- 入口 URL：`http://172.30.30.58:8081/`。
- 初始 HTTP 状态：`200`。
- 最终 URL：`http://172.30.30.58:8081/login?redirect=/user/profile`。
- 页面标题：`瑛泰管理系统 - 登录`。
- 页面正文：`瑛泰数字化平台 / 登录 / 芋道源码 / 记住我 / 忘记密码? / 登录`。
- 控制台错误：`0`。
- 控制台警告：`0`。
- 失败请求：`0`。
- HTTP 4xx/5xx 响应：`0`。
- 截图证据：`D:\ProjectPackage\Int\IntRuoyiMaintance\output\playwright\20260731-test-server-homepage-e2e\homepage.png`。
- 结构化结果：`D:\ProjectPackage\Int\IntRuoyiMaintance\output\playwright\20260731-test-server-homepage-e2e\result.json`。

## 结论

测试服务器首页可由真实浏览器访问；未登录状态下正常跳转到登录页 `http://172.30.30.58:8081/login?redirect=/user/profile`，页面渲染正常，无控制台错误、无失败请求、无 4xx/5xx 资源响应。
