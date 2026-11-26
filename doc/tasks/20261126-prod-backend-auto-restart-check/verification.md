# 正式服后端自动重启核查

核查时间：2026-11-26T10:23:36+08:00；目标：172.30.30.57。

正式服intruoyi-backend当前Docker RestartPolicy.Name=unless-stopped，backend进程/容器异常退出由Docker重启；人工停止后不属于自动拉起场景。当前Running=true、RestartCount=0、OOMKilled=false，后端健康HTTP200/status=UP。前端同为unless-stopped。Docker服务active/running且enabled，服务自身Restart=always。

当前后端Docker Healthcheck未配置；本项目独立健康恢复unit未找到，/etc/intruoyi-service-recovery目录和已登记安装入口均不存在，未发现service_recovery.py进程。因此已证实的能力止于进程退出自动拉起；进程存活而接口卡死/不健康的自动恢复尚未启用。仓库内存在自动恢复实现不等于正式服已安装。

未停止后端、未注入故障、未执行Docker restart/update、未安装/启用/arm控制器、未改业务或服务器配置。本次是配置及当前状态核查，未进行正式服故障演练。

证据：runtime-readonly-evidence.json，探针check-runtime.py。探针首次因远端Python3.6不支持capture_output失败；改用同等subprocess.PIPE后原只读检查通过，原诊断私密保存。
