#!/usr/bin/env python3
"""Download a copy of the current SQLite database.

Usage:  uv run python download_db.py [output_path]

Default output: dy_backup_YYYY-MM-DD.db
"""

import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import settings


def main():
    raw_url = settings.database_url
    if not raw_url.startswith("sqlite:///"):
        print(f"❌ Not a local SQLite database: {raw_url}")
        sys.exit(1)

    db_path = Path(raw_url.replace("sqlite:///", ""))
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(f"dy_backup_{date.today()}.db")
    shutil.copy2(db_path, output)
    size_kb = output.stat().st_size / 1024
    print(f"✅ Database copied to {output} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
