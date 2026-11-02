"""Reuse the reviewed idle/config/history guard for the resource extension."""
from pathlib import Path
import sqlite3

source=Path(__file__).with_name('apply-runtime-update.py').read_text('utf-8')
source=source.replace("private=root/'private/post-release-cleanup-20261102'",
                      "private=root/'private/post-release-cleanup-20261102/resource-extension'")
source=source.replace("private/'candidate-source-v3/ops/spug/release-center'",
                      "private/'candidate-source-v3/ops/spug/release-center'")
source=source.replace("if path.exists():shutil.copyfile(path,backup/row['name'])",
    "if path.exists():\n            (backup/row['name']).parent.mkdir(parents=True,exist_ok=True)\n            shutil.copyfile(path,backup/row['name'])")
source=source.replace("evidence=dict(pid=pid,processCreated=process.create_time(),configSha256=sha(config_path),state=state())",
    "evidence=dict(pid=pid,processCreated=process.create_time(),configSha256=sha(config_path),state=state())\n"
    "    shutil.copyfile(config_path,private/'executor.before.private.json')\n"
    "    with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\\\','/')+'?mode=ro',uri=True) as original:\n"
    "        with sqlite3.connect(private/'state.before.private.sqlite3') as snapshot:original.backup(snapshot)")
exec(compile(source,str(Path(__file__).with_name('apply-runtime-update.py')),'exec'))
