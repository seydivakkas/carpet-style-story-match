"""
Module wrapper for smoke_motif_vlm CLI tool.
Allows running via: python -m app.scripts.smoke_motif_vlm --image <path>
"""
import sys
import subprocess
from pathlib import Path

def main():
    current = Path(__file__).resolve()
    root_dir = current
    while root_dir.parent != root_dir:
        if (root_dir / "scripts" / "smoke_motif_vlm.py").exists():
            break
        root_dir = root_dir.parent

    script_path = root_dir / "scripts" / "smoke_motif_vlm.py"
    cmd = [sys.executable, str(script_path)] + sys.argv[1:]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
