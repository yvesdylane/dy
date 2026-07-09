#!/usr/bin/env python3
"""Standalone script to sync old backup DB into the current v2 DB.

Usage:  uv run python sync_backup.py [backup_file]
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from db.sync import sync_from_backup

BACKUP_FILE = Path(__file__).parent / f"dy_backup_{date.today()}.db"


def main():
    backup_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BACKUP_FILE
    if not backup_path.exists():
        print(f"\u274c Backup file not found: {backup_path}")
        sys.exit(1)

    print(f"Backup: {backup_path}")
    print(f"Target: {settings.database_url}")
    print()

    result = sync_from_backup(str(backup_path))
    print(result)


if __name__ == "__main__":
    main()
