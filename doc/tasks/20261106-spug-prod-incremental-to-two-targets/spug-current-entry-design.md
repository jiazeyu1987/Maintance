# Spug 重启后的当前进程核验

## Current Status

implementation_verified；I2 submit预检r1因历史PID152321已退出而失败，没有提交I2。修复后的3方法及9负向子项、实际固定容器只读均PASS/native0/0.405秒，14程序/7配置及当前PID9完整身份通过。完整新鲜预检仍待验证。

## 目标与设计

在固定原Spug容器内，先逐SHA验证原14程序/7配置，唯一匹配原完整argv的当前进程还须满足原cwd、executable、父进程及完整环境SHA。记录新的pid/startTicks并在读取完成后再次核对，保留原安装身份，不改写旧记录。不能把历史安装时PID当作永久运行态条件，也不能仅发现一个端口或同名进程就放行。

## BDD、里程碑及验证

- Given安装字节未变但进程正常重启；When实时核验；Then记录当前唯一身份及原PID，保持旧安装记录，允许继续其它实时检查。
- Given无唯一进程、argv/目录/可执行/环境/父进程漂移或读取期间进程变化；When核验；Then fail fast。
- 实际只读扫描已证：原21份字节全相同，当前PID9/parent1/startTicks18176，argv/cwd/executable/environment全匹配。证据PRIVATE/spug-current-pid-readonly-r1.native.private.json，native0。
- RED：`unittest test_spug_current_entry_identity` -> 3方法/11错误，实际容器节点原PID缺失，纯协议helper缺失；无写入或重启。
- 待GREEN：纯正负合同、实际固定容器只读及新鲜完整预检；不延长原预算、不代替后续真实UI。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。当前唯一完整身份严格核验是正式运行态条件；没有端口/名字放行或对失败回退。
- 是否从根因和长期维护角度解决：是。区分不可变安装字节与当前进程生命周期。
- 是否存在临时补丁或绕过：否。原PID和历史安装不改，NAS、业务服务及Spug进程不修改。

## 经验门禁

Trigger：已安装Spug正常重启；Preflight check：固定容器、21个原pins、完整原进程属性及唯一当前进程；Blocker：歧义/漂移/中途变化；Verification：纯异常合同及实际只读；Forbidden action：改旧PID、只认端口、重启环境、吞掉身份失败；Evidence：上述扫描、预检r1失败及本任务执行日志。
