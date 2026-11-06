"""Preserve the second failed attempt with separate immutable names and receipts."""
from pathlib import Path

def reviewed_template():
    path=Path(__file__).with_name('preserve_failed_attempt.py')
    text=path.read_text(encoding='utf-8')
    replacements=[
        ('History361','History362'),
        ('smallapp-181aec2e16c94e259f875c0e64eb863a','smallapp-d7a963eb1e9a4c16826c92d5753b30c3'),
        ('retained-recovery-clearance.json','health-recovery-clearance.json'),
        ("clearance['originalFailurePinsUnchanged']==205","clearance['originalFailurePinsUnchanged']==908"),
        ('restore-attempt-361','restore-attempt-362'),
        ('failed-restore-361-local-originals','failed-restore-362-local-originals'),
        ('failed-attempt-archive.json','health-failed-attempt-archive.json'),
        ('failed-attempt-preservation.json','health-failed-attempt-preservation.json'),
        ('database-state-failure-diagnosis.json','healthcheck-failure-diagnosis.json'),
        ("len(diagnosis['evidencePins'])==205","len(diagnosis['evidencePins'])==703")]
    for old,new in replacements:
        assert old in text,'PRESERVATION_CONTEXT_CHANGED'
        text=text.replace(old,new)
    return path,text

if __name__=='__main__':
    path,text=reviewed_template()
    exec(compile(text,str(path),'exec'),dict(__name__='__main__',__file__=str(path)))
