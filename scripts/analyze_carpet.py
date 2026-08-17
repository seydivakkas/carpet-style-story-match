"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Root wrapper for V2-04 Carpet Analysis Developer CLI.
"""
import sys
import asyncio
from pathlib import Path

# Ensure apps/api is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from app.scripts.analyze_carpet import main

if __name__ == "__main__":
    asyncio.run(main())
