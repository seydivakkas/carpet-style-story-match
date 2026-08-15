"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production Configuration Checker CLI.
Validates application settings against production hardening requirements.
Returns exit code 0 on success, exit code 1 on validation failure.
"""
import sys
import argparse
from app.core.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Carpet Style & Story Match Production Configuration")
    parser.add_argument("--env", type=str, default=None, help="Override APP_ENV mode (e.g. production)")
    args = parser.parse_args()

    try:
        current_settings = Settings()
        if args.env:
            current_settings.APP_ENV = args.env

        print("============================================================")
        print("Production Configuration Audit")
        print("============================================================")
        print(f"Environment Mode:  {current_settings.APP_ENV}")
        print(f"Debug Flag:        {current_settings.DEBUG}")
        print(f"Storage Backend:   {current_settings.STORAGE_BACKEND}")
        print(f"DB Pool Size:      {current_settings.DB_POOL_SIZE}")
        print(f"Rate Limit:        {current_settings.RATE_LIMIT_PER_MINUTE} req/min")
        print("------------------------------------------------------------")

        current_settings.validate_production_config()
        print("[SUCCESS] Production configuration audit PASSED cleanly.")
        print("============================================================")
        sys.exit(0)
    except Exception as exc:
        print(f"[FAIL] Production configuration audit FAILED: {exc}", file=sys.stderr)
        print("============================================================", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
