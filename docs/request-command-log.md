# 请求与命令记录

## 2026-06-16 拆分运行控制台独立应用

- 用户需求：把 IntRuoyi 的运行控制台拆成 `D:\ProjectPackage\Int\IntRuoyiMaintance` 下的独立本机应用，复制 `AGENTS.md`，初始化 Git 管控；独立应用不用芋道权限，默认本机访问，一键启动，管理现有 IntRuoyi 源码。
- 计划边界：不删除或改造原 IntRuoyi 运行控制台入口/API；本次验证不执行真实发布、备份、恢复、回滚、重启或远端清理。
- 命令记录：`python -X utf8 scripts\verify_contracts.py` RED 失败后实现代码，最终 PASS。
- 命令记录：`mvn -f backend/pom.xml test` PASS。
- 命令记录：`pnpm --dir frontend install --lockfile-only` 生成 lockfile。
- 命令记录：`pnpm --dir frontend install --frozen-lockfile` PASS。
- 命令记录：`pnpm --dir frontend typecheck` PASS。
- 命令记录：`pnpm --dir frontend build` PASS。
- 命令记录：`.\scripts\build.ps1` PASS。
- 命令记录：`.\scripts\start.ps1` 后 `curl.exe -s http://127.0.0.1:48181/actuator/health` PASS，返回 `{"status":"UP"}`。
- 命令记录：Playwright 打开 `http://127.0.0.1:48181/`、检查 snapshot、console、requests，并点击“预览命令”；页面可见且 console error 为 0，未执行真实动作。
