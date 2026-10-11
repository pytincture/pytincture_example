"""Print private login totals from the persistent metrics database."""

import argparse
import json
import os
from pathlib import Path

from . import LoginStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", default=os.getenv("PYTINCTURE_EXAMPLE_LOGIN_DB", "/data/login_metrics.sqlite3")
    )
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.days <= 3650:
        parser.error("--days must be between 1 and 3650")
    if not Path(args.database).is_file():
        parser.error("login metrics database does not exist")
    print(json.dumps(LoginStore(args.database).report(args.days), indent=2))


if __name__ == "__main__":
    main()
