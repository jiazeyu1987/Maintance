# 存储合同实现记录

## 范围与门禁
- 仅本机隔离worktree内的替换存储模块与测试，不提交Git、不连接服务器、不执行恢复。
- Trigger：正式主实例bind挂载不符合v1 volume-only合同。
- Preflight check：v1行为保持；v2按目录device/inode和mountinfo身份绑定，核protectedRoots、重叠RW消费者与本地文件系统；修改前先写BDD和失败测试。
- Blocker：资源路径、挂载、保护根或目录身份无法核准时拒绝；测试失败不得提交或假称恢复成功。
- Verification：RED/GREEN/REGRESSION命令、纯合同测试与Linux本机真实临时目录/volume测试分别记录。
- Forbidden action：禁止以放宽Type条件代替正式合同；禁止远端写入或恢复；禁止把测试fixture当三服运行证据。
- Evidence：本文件及test_replacement_storage.py，主任务已有三服只读证据。

## BDD
- BDD: 显式版本兼容 -> Given既有v1独立local named volume，When检查目标，Then仍允许；v1 bind必须拒绝。
- BDD: 正式bind身份 -> Given v2登记了本地数据目录device/inode与mountinfo，When检查未变化目录，Then允许；目录、挂载、类型或保护边界变化必须拒绝。
- BDD: 共享写入与保护范围 -> Given三服务各自写目录，When其他容器（包括停止的容器）存在同路径、祖先或后代RW挂载，或目录与NAS/归档/状态/执行路径相交，Then拒绝且不调用任何写命令。
- BDD: 复核 -> Given通过首次检查，When停服务后进入清库/清附件/清Redis阶段，Then再次检查身份和存储边界；失败保留并停止，不换路径。

- 环境前置：bundled Python无pytest，首次命令为依赖失败，不记业务RED。将pytest==8.3.5及依赖安装到任务专用 C:/Users/D01021/AppData/Local/Temp/spug-restore-targets-pytest，未修改全局Python。
- RED: PYTHONPATH=<task pytest dir> bundled-python -m pytest -q scripts/tests/test_replacement_storage.py -> FAIL，ModuleNotFoundError: recovery_replacement_storage，预期新正式存储合同尚不存在；测试收集已到真实测试文件。
- GREEN: 新存储模块及v1回归 -> Windows pytest 38 passed, 3 skipped；3项Linux路径/挂载测试明确未在Windows执行，后续在本机Docker真实临时volume执行。
- GREEN: experience-preflight -> PASS（仅本机Docker测试资源）：源码挂载只读；任务唯一容器名spug-restore-storage-unit-20261104，任务唯一volume名spug-restore-storage-unit-20261104；只写该volume的临时目录和容器层，不挂docker.sock、不连接三服、不恢复备份或改产品运行态。完成后只清理该精确测试volume。
- RED: 首次Linux真实目录测试 -> 39 passed, 2 failed；Docker Desktop的无关9p挂载source包含转义反斜杠，解析器错误拒绝完整mountinfo。
- RED: test_mountinfo_preserves_unrelated_windows_backslash_source -> FAIL；先补可独立复现的解析测试，限定只对实际受控目录执行规范Linux路径约束。
- GREEN: 修正mountinfo解码 -> 本机Docker中42 passed；真实目录device/inode、目录替换、symlink拒绝与停用容器共享写目录扫描均执行。
- RED: 物理bind别名测试 -> ImportError: physical_location；先给出同一device下/data/minio与/alias/minio映射同一目录的场景。
- GREEN: 新增mountinfo root/mountPoint物理映射，同时拒绝保护根别名及多数据目录物理重叠；Windows41 passed, 3 skipped。
- BDD: 写入前完整预检 -> Given主程序具有replacement_preflight，When进入prepare，Then归档兼容性与实例运行配置校验先于任何清库/清文件/清Redis。
- RED: test_native_preflight_runs_before_any_replacement_prepare -> FAIL；只调用storage，未调用main-inputs。
- GREEN: prepare开头调用正式preflight钩子；Windows42 passed, 3 skipped；Linux45 passed。
- BDD: 真实主库命名 -> Given主实例数据库名ruoyi-vue-pro，When校验覆盖合同，Then允许该受限标识符；反引号、空格、路径和超长标识符必须拒绝。
- RED: pytest -q scripts/tests/test_replacement_storage.py -k replacement_database -> 1 failed, 5 passed；旧正则拒绝ruoyi-vue-pro。
- GREEN: 正则仅扩展为[A-Za-z][A-Za-z0-9_-]{0,63}；Windows48 passed, 3 skipped；Linux51 passed。
- BDD: 挂载可写 -> Given挂载或底层superblock为ro，When登记v2存储，Then拒绝，不能误判为可覆盖目录。
- RED: pytest -q scripts/tests/test_replacement_storage.py -k read_only_mount -> 1 failed, 1 passed；底层superOptions=ro未被拒绝。
- GREEN: 同时校验mount options及superOptions必须rw且不含ro；最终Windows50 passed, 3 skipped；Linux53 passed。
- REGRESSION: `$env:PYTHONPATH='C:/Users/D01021/AppData/Local/Temp/spug-restore-targets-pytest'; & 'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -m pytest -q scripts/tests/test_replacement_storage.py scripts/tests/test_smallapp_replacement.py` -> 50 passed, 3 skipped in 0.48s；仅POSIX真实目录3项skip。
- REGRESSION: 本机`docker run --rm --name spug-restore-storage-unit-20261104 --mount type=bind,source=<task worktree>,target=/src,readonly --mount type=volume,source=spug-restore-storage-unit-20261104,target=/storage --workdir /src python:3.12-bookworm sh -ec 'pip install --quiet --root-user-action=ignore pytest==8.3.5 jsonschema==4.23.0; python -B -m pytest -q -p no:cacheprovider --basetemp=/storage/pytest5 scripts/tests/test_replacement_storage.py scripts/tests/test_smallapp_replacement.py'` -> 53 passed in 0.89s；真实Linux目录与挂载观测全部执行。
- REGRESSION: `git diff --check -- ops/recovery/recovery_replace.py ops/recovery/recovery_replacement_storage.py scripts/tests/test_replacement_storage.py doc/tasks/20261104-spug-selectable-restore-targets/storage-execution-log.md` -> PASS。
- Closeout：确认任务测试volume为local、名称精确匹配且无任何容器使用后，`docker volume rm spug-restore-storage-unit-20261104`成功；测试容器均以--rm退出。任务专用host Python依赖目录保留给主任务与其他子任务只读复用，不提交Git。

## 接口与验证边界
- replacement/v1原5项结构继续使用独立local named volume；v2严格增加storage，不放宽v1 Type限制。
- storage为RegisteredReplacementStorage/v1，包含protectedRoots及mounts；每项按role/type/source/destination绑定device/inode/mountIdentity。mountIdentity固定mountId、parentId、device、root、mountPoint、filesystem、source、options、superOptions。
- protectedRoots必须显式含/mnt/nas，并覆盖实际archiveRoots、operation root、replacement stateRoot与target dataRoot；按namespace路径及mountinfo物理别名双重检查相交。
- observe_directory、snapshot_mounts与verify_storage均不创建、删除或移动受控数据；读取真实目录并拒绝祖先symlink、目录身份/mountinfo漂移、远程/overlay/root/nested挂载与其他容器RW重叠。
- 原machine-id、Docker engine、container ID、image ID、labels、完整mounts、database UUID校验保留；prepare在停服后和每项清除动作前重新核验。主程序运行时后续阶段由main-runtime子任务复核。
- Windows纯合同测试不能证明Linux目录身份；3项POSIX专属测试在Windows明确skip，随后使用本机Linux容器与独立真实local volume运行全部测试，不使用三服数据。
- 本文件测试替代不了真实Spug E2E、服务器安装或恢复验证；本子任务没有执行恢复、停服、远程写入，也没有对正式/测试数据作操作。

## 消费者批量核验补充
- Trigger：main bound在SQL/文件guard重复核验，逐容器docker inspect导致188/114+消费者时超过5秒SQL guard门禁。
- BDD: 完整批量消费者核验 -> Given包含运行及停止容器的Docker清单，When每次核验写存储消费者，Then仅执行一次ps --all及一次批量inspect，同时逐项保持RW路径和物理别名检查；返回ID缺失、重复、多出或目标未列出必须拒绝。
- 设计：不缓存结果、不缩小消费者范围；减少CLI进程次数，使用本次ps完整ID集合验证本次批量inspect结果。
- Verification：先补批量次数/完整性失败测试，再最小实现；Windows合同回归与本机Linux真实目录回归分别执行。
- RED: bundled-python -m pytest -q scripts/tests/test_replacement_storage.py -k consumer -> 7 failed；旧实现未批量inspect，且缺失/重复/多出ID或目标未列出未拒绝。
- GREEN: 以本次完整ps ID集合调用一次批量inspect并检查完整唯一返回；Windows57 passed, 3 skipped。补充114/188消费者规模仍固定每轮2次消费者CLI，连续两轮均重新读取。
- GREEN: experience-preflight -> PASS（仅本机Linux回归）：重新创建本任务精确名称测试volume，源码只读、不挂docker.sock、不连接三服，运行后仅清理本任务volume及--rm测试容器。
- REGRESSION: bundled-python -m pytest -q scripts/tests/test_replacement_storage.py scripts/tests/test_smallapp_replacement.py -> 59 passed, 3 skipped in 0.54s；本机Linux同文件集 -> 62 passed in 1.40s；diff --check -> PASS。
- Closeout：Linux测试容器以--rm退出；检查精确volume名、local驱动且无容器引用后，docker volume rm spug-restore-storage-unit-20261104成功。本轮仍无服务器连接或恢复。
- 边界：114/188规模测试验证CLI次数恒定与集合完整性；本机Linux真实目录测试使用实际挂载观测。未把这些数据称为三服5秒内实测，远程性能仍需授权环境核验。

## nsfs与显式local bind-backed卷
- Trigger：本机私密只读安装证据确认.58 mountinfo含nsfs net:[inode]，.59三数据卷为ext4本地目录bind-backed local卷；旧规则误拒不相关nsfs与明确的volume子目录挂载根。
- 设计约束：storage/v1及replacement/v1严格行为不变；新storage/v2显式固定volume名称、driver、完整options、mountpoint和底层目录device/inode/mountinfo。不按失败重试或自动放宽；生成v2必须显式volume_inspector。
- BDD: nsfs保留 -> Given mountinfo含nsfs net:[inode]，When解析完整挂载表，Then保留该行、允许非存储namespace根；当nsfs被选作数据或嵌入数据目录时仍拒绝。
- BDD: 本地bind-backed卷 -> Given local卷固定type=none、o=bind及真实底层目录，When观察登记及复核，Then仅目录非文件系统根且两端同device/inode/物理路径时允许；options、底层目录、挂载、共享消费者或保护根漂移必须拒绝。
- BDD: 版本边界 -> Given旧v1配置或未显式传volume_inspector，When遇到bind-backed卷，Then保持拒绝；网络卷、rbind、设备路径和文件系统根不能变为可覆盖存储。
- Preflight check：只读取本机private库存必要Mounts/mountinfo；不输出环境、密码或连接串；不连接三服或提交Git。
- Verification：先RED再实现；纯结构/漂移测试和本机Linux真实bind挂载验证分别记录。
- RED: pytest -q scripts/tests/test_replacement_storage.py -k 'nsfs or explicit_bind_backed' -> 2 failed；旧解析拒namespace根，旧合同不接受显式storage/v2。
- GREEN: 新schema正式绑定volume定义与底层目录；Windows纯合同71 passed, 3 skipped，继续增加真实Linux bind及nsfs nested覆盖。
- GREEN: experience-preflight -> PASS（本机真实bind单元验证）：仅任务容器增加SYS_ADMIN以在独立local测试volume内部创建/卸载bind，源码只读，不挂docker.sock、不连接三服；finally卸载明确测试mountpoint，--rm退出并清理唯一任务volume。
- REGRESSION: Windows同文件集79 passed, 5 skipped in 0.61s；本机Linux `docker run --rm --name spug-restore-storage-unit-20261104 --cap-add SYS_ADMIN --mount type=bind,source=<task worktree>,target=/src,readonly --mount type=volume,source=spug-restore-storage-unit-20261104,target=/storage --workdir /src python:3.12-bookworm sh -ec 'pip install --quiet --root-user-action=ignore pytest==8.3.5 jsonschema==4.23.0; python -B -m pytest -q -p no:cacheprovider --basetemp=/storage/bind-backed-final scripts/tests/test_replacement_storage.py scripts/tests/test_smallapp_replacement.py'` -> 84 passed in 2.56s。
- 验证包括真实Linux mount --bind的两端device/inode/物理位置、旧API拒挂载根、新API生成v2、运行复核、options漂移拒绝、底层目录身份拒绝、停止容器通过底层bind别名共享拒绝，以及nsfs保留、选作数据拒绝和nested拒绝。Docker volume inspect响应为固定合同测试边界；真实目录与mountinfo来自本机Linux，不作为三服恢复实测。
- API：`snapshot_mounts(rows, protected_roots, volume_inspector=inspect_volume)`；`inspect_volume(name)`返回恰好一项Docker volume-inspect字典（至少Name/Driver/Options/Mountpoint），调用方应核原始数组长度为1；模块再次核Name/Driver/Mountpoint。无callback输出storage/v1；有callback输出storage/v2。只有type=volume项新增volume字段；其他bind项结构不变。
- v2的volume字段：`{name,driver,options,mountpoint,backing}`；完整options固定为原值（空配置保持None或{}），bind-backed仅接受type=none与o=bind或bind,rw（无重复）；backing包含`{source,device,inode,mountIdentity}`，其source必须等于options.device，且为localFS的真正子目录。数据卷正好位于其bind挂载点时，仅在底层非文件系统根、两端身份与物理路径一致、保护根及全部其他RW消费者核验通过后允许。
- Closeout：真实bind测试finally已卸载；--rm容器均退出；核专用volume精确名称、local驱动且无容器引用后，docker volume rm spug-restore-storage-unit-20261104成功。未连接三服、写入服务器、安装owner/controller或提交Git。

## 显式宿主bind的local卷
- Trigger：新版真实.59预检确认volume Options为None/{}，实际子目录bind由宿主管理。Options-driven合同无法表达该事实。
- BDD: 显式宿主bind -> Given Options空且安装输入明确指定volume_backing_paths[name]，When观察真实卷及底层目录，Then只有卷路径正好为本地子目录挂载点、两端device/inode与物理位置一致时接受，Options原样固定；未显式指定时保持拒绝。
- BDD: 不猜测资源 -> Given缺失、未知volume名或不匹配backing，When生成合同，Then明确失败，不从mountinfo自动拼装backing，不修改options，不切换目录。
- 设计约束：沿用storage/v2显式backing字段；旧v1不变。要求数据挂载与底层挂载是不同mountId、同filesystem/source/device，底层为文件系统内真正子目录；保护根、nested、符号链接与全部RW消费者校验继续生效。
- Verification：先RED Options空的纯合同与新snapshot API，再GREEN；本机Linux真实bind分别覆盖Options None/{}，不连接服务器、不提交。
- RED: pytest -q scripts/tests/test_replacement_storage.py -k 'host_managed or explicit_inspector' -> 4 failed, 1 passed；旧合同拒Options空+backing，新API尚无volume_backing_paths。
- GREEN: 显式输入与宿主子目录挂载身份校验实现后，Windows87 passed, 5 skipped；增加Options None/{}的真实bind复核、空options精确漂移与未知输入拒绝回归。
- GREEN: experience-preflight -> PASS（本机宿主bind合同回归）：同一精确任务容器/volume，SYS_ADMIN仅用于volume内部真实bind，finally卸载，源码只读，无docker.sock/远程操作，完成后清理唯一测试资源。
- REGRESSION: Windows同文件集91 passed, 7 skipped in 0.58s；本机Linux同文件集（--cap-add SYS_ADMIN，basetemp=/storage/host-bind）98 passed in 1.65s；git diff --check -> PASS。
- 实际Linux bind用例分别运行driver Options、Options=None、Options={}三种合同；每种执行snapshot与runtime复核、未显式路径的mount-root拒绝、未知backing名称拒绝、Options空值精确漂移拒绝、停止容器的底层bind别名共享拒绝及保护根/身份拒绝。
- API最终形式：`snapshot_mounts(rows, protected_roots, volume_inspector=inspect_volume, volume_backing_paths={volume_name: absolute_backing_path})`。volume_backing_paths仅由安装输入显式传入；空Options不自动推断任何目录。配置只保存实际options及明确backing身份；runtime不依赖该安装参数而逐项重新观察已固定合同。
- Closeout：所有bind在finally卸载；--rm容器退出；核精确volume名/local驱动及无容器引用后，docker volume rm spug-restore-storage-unit-20261104成功。无远程操作、恢复、owner/controller安装或Git提交。
