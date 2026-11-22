"""Replace a bundle with rollback on ordinary Python/OS errors (not power loss)."""
import os
import shutil
import uuid
from pathlib import Path


def publish_bundle(pairs, workspace, replace=os.replace):
    pairs = [(Path(a), Path(b)) for a, b in pairs]
    if any(not source.is_file() for source, _ in pairs):
        raise FileNotFoundError("Incomplete staged bundle")
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    # A plain directory keeps inherited permissions; tempfile.mkdtemp() creates a
    # restrictive DACL that sandboxed Windows users cannot even clean up.
    staging = workspace / f"publish-{uuid.uuid4().hex[:10]}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        backups = []
        changed = []
        for i, (_, target) in enumerate(pairs):
            backup = staging / str(i) if target.exists() else None
            if backup:
                shutil.copyfile(target, backup)
            backups.append(backup)
        try:
            for (source, target), backup in zip(pairs, backups):
                target.parent.mkdir(parents=True, exist_ok=True)
                replace(source, target)
                changed.append((target, backup))
        except BaseException:
            for target, backup in reversed(changed):
                if backup:
                    os.replace(backup, target)
                else:
                    target.unlink(missing_ok=True)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
