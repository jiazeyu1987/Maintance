import subprocess


REPO = r"E:\IntRuoyi"
PATH = "IntRuoyiBackend/sql/mysql/20260513_dcc_base_schema.sql"

before = """INSERT INTO `system_menu`
(`id`, `name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`)
SELECT 6813, 'DCC受控打印', 'dcc:controlled-file:print', 3, 4, 6807, '', '', '', '', 0, b'1', b'1', b'1', '1', NOW(), '1', NOW(), b'0'
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `permission` = 'dcc:controlled-file:print');"""

after = """INSERT INTO `system_menu`
(`name`, `permission`, `type`, `sort`, `parent_id`, `path`, `icon`, `component`, `component_name`, `status`, `visible`, `keep_alive`, `always_show`, `creator`, `create_time`, `updater`, `update_time`, `deleted`)
SELECT 'DCC受控打印', 'dcc:controlled-file:print', 3, 4, 6807, '', '', '', '', 0, b'1', b'1', b'1', '1', NOW(), '1', NOW(), b'0'
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `permission` = 'dcc:controlled-file:print');"""

original = subprocess.check_output(["git", "-C", REPO, "show", f"HEAD:{PATH}"]).decode("utf-8")
if before not in original:
    raise SystemExit("target block missing from HEAD")

patched = original.replace(before, after, 1).encode("utf-8")
blob = subprocess.check_output(["git", "-C", REPO, "hash-object", "-w", "--stdin"], input=patched).decode().strip()
subprocess.check_call(["git", "-C", REPO, "update-index", "--cacheinfo", "100644", blob, PATH])
print(blob)
