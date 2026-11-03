from pathlib import Path
p=Path(__file__).parent
s=(p/'spug-nas-retry-ui.cjs').read_text('utf-8')
s=s.replace('original-failed-build','original-failed-test').replace('originalBuildJobId','originalDeploymentJobId').replace('nas-retry','sealed-test-retry')
s=s.replace('原包已封存且副本归属审计通过；Git删除超时后已确认登记及物理路径消失。校验原固定提交封包并重传NAS，不重新编译、不部署三服，保留失败记录。',
    '沿用原全量包和完整检查点，核原容器、挂载JAR、全表内容、GxP及零写者后仅续接程序切换与验收；不重备份、不执行迁移或恢复数据库，保留原失败。')
(p/'spug-sealed-test-retry-ui.cjs').write_text(s,encoding='utf-8')
