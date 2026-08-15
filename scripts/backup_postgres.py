"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production Database Backup Utility.
Safely invokes pg_dump to produce timestamped, compressed database backups.
Credentials are read strictly from environment variables.
"""
import os
import sys
import subprocess
from datetime import datetime, timezone


def backup_database() -> str:
    db_url = os.getenv("DATABASE_URL", "")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_user = os.getenv("POSTGRES_USER", "carpet_user")
    pg_password = os.getenv("POSTGRES_PASSWORD", "carpet_password")
    pg_db = os.getenv("POSTGRES_DB", "carpet_db")

    backup_dir = os.path.abspath("data/backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_filename = f"carpet_db_backup_{timestamp}.sql.gz"
    output_path = os.path.join(backup_dir, output_filename)

    print("============================================================")
    print("PostgreSQL Production Database Backup")
    print("============================================================")
    print(f"Timestamp:  {timestamp}")
    print(f"Host:       {pg_host}:{pg_port}")
    print(f"Database:   {pg_db}")
    print(f"User:       {pg_user}")
    print(f"Target:     {output_path}")
    print("------------------------------------------------------------")

    env = os.environ.copy()
    env["PGPASSWORD"] = pg_password

    # Command: pg_dump -h host -p port -U user dbname | gzip > backup.sql.gz
    cmd = f"pg_dump -h {pg_host} -p {pg_port} -U {pg_user} {pg_db} | gzip > \"{output_path}\""

    try:
        res = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] Database backup created successfully: {output_path}")
            print("============================================================")
            return output_path
        else:
            print(f"[ERROR] pg_dump failed: {res.stderr}", file=sys.stderr)
            print("============================================================", file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Backup process exception: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    backup_database()
