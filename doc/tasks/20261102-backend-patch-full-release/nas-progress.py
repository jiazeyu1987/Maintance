"""Read only bounded NAS transfer metadata; never print credentials or config."""
from pathlib import Path
import json
root=Path('C:/SpugHandoff/release')
config=json.loads((root/'executor.private.json').read_text('utf-8'))
selection=json.loads(Path(__file__).with_name('selected-release.json').read_text('utf-8'))
folder=Path(config['nasPath'])/selection['fullReleaseTag']
files={name:(folder/name).stat().st_size for name in ('release.tar.partial','release.tar','manifest.json') if (folder/name).is_file()}
print(json.dumps(dict(tag=selection['fullReleaseTag'],files=files)))
