# Spug continuation 精确挂载与原运行器只读观察

## Goal and Current Status

in_progress。为已批准的只读 bind 发布器重构补齐真实机器证据；不安装配置、不调用服务器。原 v2 发布失败、八阶段及 r2 状态观察全部保留。

## Milestones and verification

1. 固定原 v2 输入、FAILED、dispatch、completion、原状态及资源安装 PASS 的 pins。
2. 实际 inspect 明确的18080和受保护18081两个容器，逐一核原完整 snapshot、loopback 端口及三个精确存储挂载。全部原始输出仅保存私密文件。
3. 查询 Windows 原发布器 PID47712 已不存在；读取原容器 entry151768 的真实 /proc 身份。命令实际退出码、stdout/stderr及程序/请求逐项独占保存。
4. 仅在前后容器身份、原输入保持时产生正式 mount 观察。它是只读事实，不等同于续办发布 PASS；后续 apply 仍须核当前状态。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。任何缺失、别名、mount或进程漂移直接失败并保留原件。
- 是否从根因和长期维护角度解决：是。让宿主部署路径由真实 mount 明确绑定，保持容器运行路径只读。
- 是否存在临时补丁或绕过：否。不改变容器或运行配置，不用文字说明代替原生命令证据。

## 经验门禁

- Trigger：部分完成的正式配置发布需要只读 bind 续办。
- Preflight check：已知容器ID/端口、原snapshot和输入pins，明确原运行器终态；只查询固定两容器及原entry/Windows PID。
- Blocker：原实例或mount漂移、旧PID仍存、未知子mount、原件发生变化、任何查询非零退出。
- Verification：保存真实argv/program/stdout/stderr/actualExitCode和前后snapshot，明确runtimeWrites=false、remoteServerCalls=0。
- Forbidden action：不更改RW、不启动或重启实例、不写业务或配置、不触碰NAS/fstab、不派发备份恢复。
- Evidence：observe-spug-continuation-mount-r1.py及独立只读查询原件、spug-continuation-mount-observation-r1.json。
