# 历史数据库元数据原件只读核验

## Current Status

in_progress。108点映射已独立核过423个原件pin；54点expected-data正文未读，105点material与declared payload的关系尚未逐点核等。be26b592旧本机inventory缺副本，但较新的完整程序原件报告已核到其point/manifest/binding/material原pin，不能认定NAS损坏。

## Goal and scope

逐点获取并核验原数据库证据，不执行SQL、备份或恢复，不改变原归档/清单/历史。此动作使用已授权NAS共享只读访问，不需要服务器SSH或服务操作。

1. 从冻结映射、105个已核binding和原目录快照构造确切路径清单。首先只在映射列明的本机原件中按bytes/SHA找等值副本，不递归扫描私密根。
2. 读取54个未评估expected-data JSON（共34891694字节）和105个material（共126312403字节），合计159项/161204097字节。
3. 从已受验historical-program-archive-57-be26b59-r1.json提取原四个repository pin，只读补齐其point/manifest/binding/material，合计20179120字节。由其真实manifest/material唯一关系再读取至多一个expected-data JSON。
4. 总对象上限164，总读取上限200MiB、单文件16MiB、单文件子进程20秒、整体600秒；任一失败保存原件与准确错误，不扩大扫描或预算，不静默回退。
5. 每个成功对象完整字节/SHA、普通文件和读取前后身份检查，排他保存到新的操作私密目录。随后只解析JSON格式/数据库/点绑定/原material expectedDataPin与manifest候选关系，保留原NOT_PERFORMED状态；不产生恢复或来源快照一致性PASS。

## Expected verification

原冻结映射与输入前后pin保持；每个成功副本重新读取验证原pin；105+新增be26material关系逐点记录；54+至多新增1个数据库证据明确格式、数据/结构字段是否存在。公开报告仅事实计数、类别、失败码和私密证据pin，不含记录内容、连接串或凭据。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。失败保留具体对象，不用同组代表替代。
- 是否从根因和长期维护角度解决：是。先查真实原格式及其关系，再决定明确的长期恢复合同。
- 是否存在临时补丁或绕过：否。

## 经验门禁

Trigger：历史declared evidence未读及本地inventory副本缺口。Preflight check：固定原目录快照和映射SHA、逐pin路径、大小/总预算、UNC仅172.30.30.4公司共享BackupPackage既有根、读写目的地分离。Blocker：原pin不符、路径越界、对象/总量超限、原读进程未终态或未知格式。Verification：独占副本、逐对象实际退出与内容SHA、关系及格式报告；这不是载荷恢复验收。Forbidden action：不读取大SQL/tar/附件，不写NAS，不改原manifest，不凭文件名或代表组追认PASS，不以新派生证据冒充历史源快照。Evidence：legacy-schema-restoration-point-map.json和historical-program-archive-57-be26b59-r1.json。

### 原件采集载体的实际前置失败及修正

r2在本机构造159项清单前断言失败，未读NAS正文：两未发布点有declared payload但无binding，不能一并continue遗漏，已在r3明确独立列入而不追认material关系。r3实际163项全部失败/24.406秒，其中159项SOURCE_OPEN_CHANGED，be26四项原UNC路径FileNotFoundError；未形成有效副本。只读单文件诊断证明只有st_ctime_ns在Path.stat和os.fstat两个API间不同，而各API自身前后稳定；其余dev/ino/mode/nlink/size/mtime全等。

修正仅采集载体：跨API比较保留其余全部身份项，各API各自前后仍包含ctime完整比较；期望内容bytes/SHA及原路径/别名约束不变。唯一实际单文件probe exit0，完整65791字节原pin与副本核等。r4按同一原清单重新读159项；be26四已知缺路径不重复派发，引用r3失败原件并标明readReattempted=false。原失败不覆盖、不当业务RED，也不声明归档损坏。

GREEN: experience-preflight -> PASS。r4仍受原164项/200MiB/单文件20秒/总600秒，只读NAS、不执行SQL或服务器写入；实际worker超时先结束精确自有读进程并核终态。