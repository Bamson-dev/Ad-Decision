#!/usr/bin/env python3
"""Docker HEALTHCHECK: verify data volume and Telegram API reachability."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("healthcheck: TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        return 1

    data_dir = Path(os.getenv("ADLEY_DATA_DIR", "/data"))
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".healthcheck"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        print(f"healthcheck: data dir not writable ({data_dir}): {exc}", file=sys.stderr)
        return 1

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            if resp.status != 200:
                print(f"healthcheck: getMe HTTP {resp.status}", file=sys.stderr)
                return 1
    except urllib.error.URLError as exc:
        print(f"healthcheck: Telegram API unreachable: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
