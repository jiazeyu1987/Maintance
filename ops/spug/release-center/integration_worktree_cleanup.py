"""Explicit closeout for a clean task-owned branch already merged into main.

Example: python integration_worktree_cleanup.py --repo REPO --worktree PATH
 --root TASK_ROOT --commit FULL_SHA --branch codex/task --merged-into int_main
Only registered checkouts are accepted. Unknown residuals require investigation.
"""
import argparse
import json
from pathlib import Path
from build_worktree_cleanup import cleanup_build_worktree


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('repo','worktree','root','commit','branch','merged-into'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--proof',required=True,help='External task-owned receipt for interrupted cleanup retry')
    args=parser.parse_args()
    proof_path=Path(args.proof).resolve()
    if proof_path.is_relative_to(Path(args.worktree).resolve()):
        parser.error('proof must be outside removed checkout')
    prior=json.loads(proof_path.read_text(encoding='utf-8')) if proof_path.exists() else None
    def save(value):
        temporary=proof_path.with_suffix(proof_path.suffix+'.tmp')
        temporary.write_text(json.dumps(value),encoding='utf-8')
        temporary.replace(proof_path)
    result=cleanup_build_worktree(args.repo,args.worktree,args.root,args.commit,
        integration_branch=args.branch,merged_into=args.merged_into,prior_proof=prior,before_remove=save)
    result.update(mergedInto=args.merged_into,branch=args.branch)
    print(json.dumps(result))


if __name__=='__main__':
    main()
