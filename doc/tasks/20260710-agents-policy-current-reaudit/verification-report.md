# 当前 AGENTS 与经验规则独立复审报告

## 结论

**PASS**：修复本轮发现项后，当前审计范围内没有仍会导致执行动作互斥、状态机循环、环境越界或验证降级的未解决逻辑冲突。

## 审计范围

- 全局规则：`C:\Users\BJB110\.codex\AGENTS.md`
- 父级规则：`D:\ProjectPackage\AGENTS.md`、`D:\ProjectPackage\Int\AGENTS.md`
- 项目规则：维护仓与 IntRuoyi 的 `AGENTS.md`
- 经验入口：两个项目的 `docs/experience-index.md`
- 专项规则：PowerShell、登录/E2E、worktree、测试服发布、发布检查清单、发布经验
- 收尾规则：`task-closeout-cleanup` skill、closeout rules 和脚本回归测试

## 已发现并修复

| 等级 | 问题 | 处理结果 |
| --- | --- | --- |
| P1 | “先创建任务文档”与“任务开始先读经验索引”顺序相反 | 两个经验索引和测试服发布入口统一为先创建最小任务文档，再读索引并补齐门禁 |
| P1 | PowerShell 规则要求第一条命令前读取经验，但读取本身通常依赖命令 | 定义唯一允许的 UTF-8 只读 bootstrap；读取完成前禁止写入、外部调用和业务命令 |
| P1 | 芋道源码租户只读基线与“普通明确授权即可写入”并存 | 普通授权不再构成写入许可；必须由用户明确覆盖 AGENTS 禁令并限定范围 |
| P2 | 完整发布清单可能让仅测试服任务继续进入 mark-tested/正式服/备份服 | 在八步流程旁明确仅测试服于测试运行态验证后停止 |
| P2 | 泛化“任务完成后提交”可能与实现提交、收尾提交两阶段状态机冲突 | 两个项目 AGENTS 统一为实现提交与最终收尾记录提交两阶段 |

## 无冲突项

- Playwright 版本、运行目录和浏览器路径只有 `D:\ProjectPackage\AGENTS.md` 定义共同规则，子级仅继承。
- `ready_for_closeout -> cleanup -> completed` 状态机在全局、项目、worktree、发布经验和 cleanup skill 中一致。
- 测试服完整运行态验证与仅测试服环境边界一致；测试服任务明确禁止 `mark-tested`、正式服和备份服动作。
- 写入型 E2E 默认只允许测试租户并必须走真实前端；API 仅用于最终核验。
- 同名分支只覆盖实际参与且需要修改的仓库；无关仓库不得创建占位分支。
- 六字段经验摘要为唯一格式，旧四段仅允许作为详细展开。

## 验证证据

- 策略断言：PASS，旧冲突文本无命中，新权威文本全部存在，测试服使用顺序正确。
- task-closeout 单元测试：3/3 PASS。
- task-closeout skill quick validation：PASS。
- Playwright 共同规则扫描：仅父级权威文件命中。
- closeout 状态机扫描：全局、项目、worktree、发布经验和 skill 一致。
- 两仓目标文件 `git diff --check`：PASS。
- 所有本轮目标文件 UTF-8 严格解码：PASS。

## 边界说明

- 重复出现的 BDD/TDD、UTF-8、fail-fast 条款属于同向加严，不构成互斥冲突。
- 业务仓 `AGENTS.md` 原有的标准列表模板和 PowerShell 增量规则属于其他任务改动，本任务不会将其纳入提交。
- 两个仓库其余既有脏改保持原样，不作为本任务清理对象。
