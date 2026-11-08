# 原始验收记录的 Git 空白检查

## Current Status
completed

## 目标与设计约束检查

保留已被 SHA256 引用的验收原件字节，同时让 Git 区分 CRLF 行尾、原始测试输出的结尾空行与真实源码空白问题。当前 `.gitattributes` 的 `* -text` 禁止转换字节，但默认空白检查把 117 个文件的 7629 个 CRLF 行尾报告为 trailing whitespace。按 CRLF 识别后仅剩两个原始测试输出末尾空行。

- 是否引入 fallback/降级/吞异常：否。仍检查真实行尾空格、tab 前空格及普通文件末尾空行。
- 是否从根因和长期维护角度解决：是。使用任务目录的 Git 属性表达原件的字节和行尾契约。
- 是否存在临时补丁或绕过：否。不改写历史验收文件，不跳过 diff 检查，不修改全局 Git 配置。

## BDD / TDD 与里程碑

1. Given 带 CRLF 的原始记录，When 按本目录属性暂存，Then 暂存字节完全相同且合法 CRLF 不报错。
2. Given 两份已确认原始测试输出，When 它们含末尾空行，Then 仅这两条精确路径允许原始输出格式。
3. Given 源码含行尾空格或普通文件含末尾空行，When 执行 Git diff --cached --check，Then 仍失败。
4. RED 后最小更新属性；GREEN 后核真实已暂存集合仅为本次 selection 内 886 个文件，保留失败回执，再按精确路径解除本次暂存并重新准备新清单。

## 经验门禁

原始失败回执不覆盖；不自动 reset。先人工核对暂存路径全部属于当前 selection，HEAD 未变化且无其它任务暂存。仅允许解除本次明确 886 个路径的暂存，保留工作区全部字节；重新精确提交前再审查新清单。42 项旧资产不进入提交，主线不变，所有敏感原文仍只存 PRIVATE。

## 实际失败

2026-11-08：records-execute-acceptance-1.json 已完成扫描（74 个已知私密值、零命中），暂存 886 路径后真实失败 STAGED_DIFF_CHECK_FAILED_REVIEW_INDEX；未产生提交，HEAD 仍为 0dc7429d4758a208a5b0c098111fe9702ab63235。全部暂存路径均在原 selection 内；原始检查 7629 条行尾错误；按 cr-at-eol 复查只剩 automatic-closeout-helper-regression-r2.txt:29 和 catalogue-login-helper-r4-regression.txt:12 的原始输出末尾空行。

## 验证结果

RED：真实临时 Git 仓库中 3 个合法原始格式场景失败、2 个非法空白场景正确拒绝。GREEN：任务目录声明 cr-at-eol、仅上述两条精确原始日志路径声明允许 blank-at-eof 后，5 项全部通过；每个场景均验证 Git 暂存原文 bytes 完全相同。真实原暂存集合再次 diff --cached --check 退出 0。已人工核对 886 个路径全部属于旧清单，按精确路径解除暂存，所有工作区字节保持、HEAD 不变且 index 空；见 record-line-ending-recovery.json。原失败回执保留，重新准备记录清单。
